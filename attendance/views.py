from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.http import JsonResponse, HttpResponseRedirect
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import authenticate, login as auth_login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.core.files.base import ContentFile
from django.core.files import File
from io import BytesIO
import qrcode
import json
import uuid

from django.contrib.auth.forms import AuthenticationForm

from .models import Module, QRCode, Attendance

@login_required
def generate_qr(request, module_id=None):
    # Get all modules for the user
    if request.user.is_superuser:
        modules = Module.objects.all()
    else:
        modules = Module.objects.filter(lecturers=request.user)
    
    # If module_id is provided in URL, pre-select it in the form
    selected_module = None
    if module_id:
        selected_module = get_object_or_404(Module, id=module_id, lecturers=request.user)
    
    if request.method == 'POST':
        module_id = request.POST.get('module', module_id)  # Use POST data if available, otherwise use URL parameter
        expiration = int(request.POST.get('expiration', 60))  # Default to 60 minutes
        if not module_id:
            messages.error(request, 'Please select a module.')
            return redirect('attendance:generate_qr')
        
        module = get_object_or_404(Module, id=module_id)
        
        # Check if there's an active QR code for this module
        existing_qr = QRCode.objects.filter(
            module=module,
            lecturer=request.user,
            is_active=True
        ).first()
        
        if existing_qr:
            messages.error(request, 'There is already an active QR code for this module.')
            return redirect('attendance:generate_qr')
        
        # Set session date based on selected expiration time
        session_date = timezone.now() + timezone.timedelta(minutes=expiration)
        
        # Create new QR code
        qr = QRCode.objects.create(
            module=module,
            lecturer=request.user,
            session_date=session_date,
            expiration_minutes=expiration
        )
        
        # Generate QR image
        qr.generate_qr_image()
        qr.save()
        
        # Send notification to all students in the module
        students = module.students.all()
        if students.exists():
            subject = f'New QR Code Available - {module.code}'
            message = f"A new QR code has been generated for {module.code} session on {session_date}.\n\nQR Code: {qr.qr_code}\n\nThis code is valid until {session_date.strftime('%Y-%m-%d %H:%M:%S')}"
            recipient_list = [student.email for student in students]
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                recipient_list,
                fail_silently=True
            )
        
        messages.success(request, 'QR code generated successfully.')
        return redirect('attendance:view_qr', qr_id=qr.id)
    
    # Calculate statistics
    total_qrcodes = QRCode.objects.count()
    active_qrcodes = QRCode.objects.filter(is_active=True).count()
    expired_qrcodes = total_qrcodes - active_qrcodes
    
    # Update QR images for existing QR codes
    for qr in QRCode.objects.all():
        if not qr.qr_image:
            qr.generate_qr_image()
            qr.save()
    
    context = {
        'modules': modules,
        'title': 'Generate QR Code',
        'selected_module': selected_module,
        'current_time': timezone.now().strftime('%Y-%m-%dT%H:%M'),
        'total_qrcodes': total_qrcodes,
        'active_qrcodes': active_qrcodes,
        'expired_qrcodes': expired_qrcodes
    }
    return render(request, 'attendance/generate_qr.html', context)

@login_required
def qr_history_modules(request):
    """View to list all modules for QR code history selection"""
    if request.user.is_superuser:
        modules = Module.objects.all()
    else:
        modules = Module.objects.filter(lecturers=request.user)
    
    return render(request, 'attendance/qr_history_modules.html', {
        'modules': modules
    })

@login_required
def qr_history(request, module_id):
    """View to show QR code history for a specific module"""
    module = get_object_or_404(Module, id=module_id)
    if not request.user.is_superuser and module not in request.user.modules.all():
        messages.error(request, 'You do not have permission to view this module.')
        return redirect('dashboard:index')
    
    qrcodes = QRCode.objects.filter(module=module).order_by('-session_date')
    return render(request, 'attendance/qr_history.html', {
        'module': module,
        'qrcodes': qrcodes
    })

@login_required
def deactivate_qr(request, qr_id):
    qr = get_object_or_404(QRCode, id=qr_id)
    if not request.user.is_superuser and qr.lecturer != request.user:
        messages.error(request, 'You do not have permission to deactivate this QR code.')
        return redirect('attendance:generate_qr')
    
    if not qr.is_active:
        messages.error(request, 'This QR code is already deactivated.')
        return redirect('attendance:generate_qr')
    
    qr.deactivate()
    messages.success(request, 'QR code has been deactivated.')
    return redirect('attendance:generate_qr')

@login_required
def extend_qr_expiration(request, qr_id):
    qr = get_object_or_404(QRCode, id=qr_id)
    if not request.user.is_superuser and qr.lecturer != request.user:
        messages.error(request, 'You do not have permission to extend this QR code.')
        return redirect('attendance:generate_qr')
    
    if not qr.is_active:
        messages.error(request, 'This QR code is deactivated and cannot be extended.')
        return redirect('attendance:generate_qr')
    
    minutes = int(request.POST.get('minutes', 15))  # Default to 15 minutes
    qr.extend_expiration(minutes)
    messages.success(request, f'QR code expiration extended by {minutes} minutes.')
    return redirect('attendance:generate_qr')

@login_required
def view_qr(request, qr_id):
    qr = get_object_or_404(QRCode, id=qr_id)
    if qr.lecturer != request.user:
        messages.error(request, 'You do not have permission to view this QR code.')
        return redirect('dashboard:index')
    
    return render(request, 'attendance/view_qr.html', {
        'qr': qr
    })

@login_required
def attendance_detail(request, module_id, qr_id):
    module = get_object_or_404(Module, id=module_id)
    qr = get_object_or_404(QRCode, id=qr_id)
    
    if qr.module != module:
        messages.error(request, 'QR code does not belong to this module.')
        return redirect('dashboard:index')
    
    if qr.lecturer != request.user and not request.user.is_superuser:
        messages.error(request, 'You do not have permission to view this attendance.')
        return redirect('dashboard:index')
    
    attendance_records = Attendance.objects.filter(qr_code=qr)
    total_students = module.students.count()
    present_students = attendance_records.count()
    
    return render(request, 'attendance/attendance_detail.html', {
        'module': module,
        'qr': qr,
        'attendance_records': attendance_records,
        'total_students': total_students,
        'present_students': present_students
    })

@login_required
def scan_qr(request):
    if request.method == 'POST':
        qr_code = request.POST.get('qr_code')
        if not qr_code:
            messages.error(request, 'QR code is required.')
            return redirect('attendance:generate_qr')
        
        try:
            qr = QRCode.objects.get(qr_code=qr_code)
            if not qr.is_active:
                messages.error(request, 'This QR code is no longer active.')
                return redirect('attendance:generate_qr')
            
            # Check if the student has already scanned this QR code
            if Attendance.objects.filter(student=request.user, qr_code=qr).exists():
                messages.error(request, 'You have already scanned this QR code.')
                return redirect('attendance:generate_qr')
            
            # Create attendance record
            Attendance.objects.create(
                student=request.user,
                qr_code=qr,
                scanned_time=timezone.now()
            )
            
            messages.success(request, 'QR code scanned successfully.')
            return redirect('attendance:generate_qr')
        except QRCode.DoesNotExist:
            messages.error(request, 'Invalid QR code.')
            return redirect('attendance:generate_qr')
    
    return redirect('attendance:generate_qr')

@login_required
def student_scan(request):
    if not request.user.is_student:
        messages.error(request, 'Access denied. This page is for students only.')
        return redirect('dashboard:index')
    
    # Get recent scans for this student
    recent_scans = Attendance.objects.filter(student=request.user).order_by('-scanned_time')[:5]
    
    return render(request, 'attendance/student_scan.html', {
        'recent_scans': recent_scans
    })

@login_required
def scan_qr_code(request, qr_code):
    if not request.user.is_student:
        return JsonResponse({'success': False, 'message': 'Access denied'})
    
    try:
        qr = QRCode.objects.get(qr_code=qr_code)
        if not qr.is_active:
            return JsonResponse({'success': False, 'message': 'This QR code is no longer active.'})
        
        # Check if the student has already scanned this QR code
        if Attendance.objects.filter(student=request.user, qr_code=qr).exists():
            return JsonResponse({'success': False, 'message': 'You have already scanned this QR code.'})
        
        # Create attendance record
        Attendance.objects.create(
            student=request.user,
            qr_code=qr,
            scanned_time=timezone.now()
        )
        
        return JsonResponse({'success': True, 'message': 'QR code scanned successfully.'})
        
    except QRCode.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Invalid QR code.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

def login_view(request):
    if request.user.is_authenticated:
        # If user is already logged in, redirect based on their role
        if request.user.is_superuser:
            return redirect('dashboard:admin_dashboard')
        elif hasattr(request.user, 'is_lecturer') and request.user.is_lecturer:
            return redirect('dashboard:lecturer_dashboard')
        elif hasattr(request.user, 'is_student') and request.user.is_student:
            return redirect('dashboard:student_dashboard')
        return redirect('dashboard:index')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            # Get the authenticated user from the form
            user = form.get_user()
            auth_login(request, user)
            
            # Set a welcome message
            messages.success(request, f'Welcome back, {user.get_full_name() or user.email}!')
            
            # Get the 'next' URL from the form or default to the dashboard
            next_url = request.POST.get('next') or 'dashboard:index'
            
            # Redirect based on user role
            if user.is_superuser:
                return redirect('dashboard:admin_dashboard')
            elif hasattr(user, 'is_lecturer') and user.is_lecturer:
                return redirect('dashboard:lecturer_dashboard')
            elif hasattr(user, 'is_student') and user.is_student:
                return redirect('dashboard:student_dashboard')
            return redirect('dashboard:index')
        else:
            messages.error(request, 'Invalid email or password. Please try again.')
    else:
        form = AuthenticationForm()
    
    return render(request, 'attendance/login.html', {
        'form': form,
        'next': request.GET.get('next', '')
    })

def logout_view(request):
    logout(request)
    return redirect('attendance:login')

@login_required
def attendance_report(request, module_id):
    module = get_object_or_404(Module, id=module_id)
    if not module.lecturers.filter(id=request.user.id).exists():
        messages.error(request, 'You do not have permission to view this report.')
        return redirect('dashboard:index')
    
    # Get all QR codes for this module
    qrcodes = QRCode.objects.filter(module=module)
    
    # Calculate attendance statistics
    total_sessions = qrcodes.count()
    student_attendance = {}
    
    for student in module.students.all():
        attended = Attendance.objects.filter(
            student=student,
            qr_code__in=qrcodes,
            status='present'
        ).count()
        percentage = (attended / total_sessions * 100) if total_sessions > 0 else 0
        student_attendance[student] = {
            'attended': attended,
            'percentage': percentage,
            'eligible': percentage >= module.attendance_threshold
        }
    
    return render(request, 'attendance/attendance_report.html', {
        'module': module,
        'student_attendance': student_attendance,
        'total_sessions': total_sessions
    })
