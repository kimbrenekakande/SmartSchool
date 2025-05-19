import json
import logging
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Avg, Count, F, Q, Sum
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.http import (
    Http404, HttpResponse, HttpResponseForbidden, HttpResponseRedirect,
    HttpResponseServerError, JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

# Try to import GDAL-related modules if available
try:
    from django.contrib.gis.geos import Point
    GEODJANGO_AVAILABLE = True
except (ImportError, OSError) as e:
    print(f"Geodjango not available: {e}")
    GEODJANGO_AVAILABLE = False
    Point = None

logger = logging.getLogger(__name__)
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
            
        # Check for overlapping sessions (within 3 hours before or after)
        new_qr = QRCode(
            module=module,
            lecturer=request.user,
            session_date=timezone.now() + timezone.timedelta(minutes=expiration),
            expiration_minutes=expiration
        )
        if new_qr.has_overlapping_session():
            messages.error(request, 'There is already a session for this module within the next 3 hours.')
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
    if not request.user.is_authenticated:
        return redirect('login')
        
    if not request.user.is_student:
        messages.error(request, 'Only students can access this page.')
        return redirect('dashboard')
        
    # Get active QR codes for the student's modules
    active_qr_codes = QRCode.objects.filter(
        module__students=request.user,
        is_active=True,
        session_date__gte=timezone.now() - timedelta(minutes=60)  # Only show codes from the last hour
    ).select_related('module')
    
    # Get recent attendance records
    recent_attendance = Attendance.objects.filter(
        student=request.user
    ).select_related('qrcode__module').order_by('-timestamp')[:5]
    
    context = {
        'active_qr_codes': active_qr_codes,
        'recent_attendance': recent_attendance,
        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY,
    }
    return render(request, 'attendance/student_scan.html', context)

@require_http_methods(["POST"])
@login_required
@csrf_exempt
def verify_biometric(request):
    """Handle biometric verification for attendance"""
    if not request.user.is_authenticated or not request.user.is_student:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)
    
    try:
        data = json.loads(request.body)
        qr_code = data.get('qr_code')
        biometric_data = data.get('biometric_data')
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        
        if not all([qr_code, biometric_data, latitude is not None, longitude is not None]):
            return JsonResponse({'success': False, 'error': 'Missing required fields'}, status=400)
            
        # Get the QR code and verify it's active
        try:
            qr = QRCode.objects.select_related('module').get(qr_code=qr_code, is_active=True)
        except QRCode.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Invalid or expired QR code'}, status=400)
            
        # Check if student is enrolled
        if not qr.module.students.filter(id=request.user.id).exists():
            return JsonResponse({'success': False, 'error': 'Not enrolled in this module'}, status=403)
        
        # Create or update attendance record
        with transaction.atomic():
            attendance, created = Attendance.objects.get_or_create(
                student=request.user,
                qrcode=qr,
                defaults={
                    'status': 'pending_verification',
                    'latitude': latitude,
                    'longitude': longitude,
                    'biometric_data': biometric_data,
                    'device_info': {
                        'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                        'ip_address': request.META.get('REMOTE_ADDR', '')
                    }
                }
            )
            
            if not created:
                # Update existing attendance record
                if attendance.biometric_verified:
                    return JsonResponse({
                        'success': True, 
                        'verified': True,
                        'message': 'Attendance already verified',
                        'attendance_id': attendance.id
                    })
                
                # Verify biometric (in a real app, you'd compare with stored biometric data)
                # For now, we'll just check if the data is present
                if attendance.verify_biometric(biometric_data):
                    attendance.biometric_verified = True
                    attendance.status = 'present'  # Final status after verification
                    attendance.save()
                    
                    # Send confirmation email
                    send_mail(
                        f'Attendance Verified - {qr.module.code}',
                        f'Your attendance has been verified for {qr.module.code} on {qr.session_date.strftime("%Y-%m-%d %H:%M")}.',
                        settings.DEFAULT_FROM_EMAIL,
                        [request.user.email],
                        fail_silently=True,
                    )
                    
                    return JsonResponse({
                        'success': True, 
                        'verified': True,
                        'message': 'Biometric verification successful',
                        'attendance_id': attendance.id
                    })
                else:
                    attendance.verification_attempts += 1
                    attendance.last_verification_attempt = timezone.now()
                    attendance.save()
                    return JsonResponse({
                        'success': False, 
                        'verified': False,
                        'message': 'Biometric verification failed',
                        'attempts_remaining': 3 - attendance.verification_attempts
                    }, status=400)
            
            # For new attendance record
            if created:
                # Check location first
                location_status = attendance.check_location()
                if location_status == 'absent':
                    attendance.status = 'absent'
                    attendance.save()
                    return JsonResponse({
                        'success': False,
                        'error': 'You are not in the correct location for this class.',
                        'location_verified': False
                    }, status=400)
                    
                # If location is verified, proceed with biometric
                # In a real app, you'd compare with stored biometric data
                # For now, we'll just check if the data is present
                if attendance.verify_biometric(biometric_data):
                    attendance.biometric_verified = True
                    attendance.status = 'present'
                    attendance.save()
                    
                    send_mail(
                        f'Attendance Verified - {qr.module.code}',
                        f'Your attendance has been verified for {qr.module.code} on {qr.session_date.strftime("%Y-%m-%d %H:%M")}.',
                        settings.DEFAULT_FROM_EMAIL,
                        [request.user.email],
                        fail_silently=True,
                    )
                    
                    return JsonResponse({
                        'success': True, 
                        'verified': True,
                        'message': 'Attendance verified successfully',
                        'attendance_id': attendance.id
                    })
                
            return JsonResponse({
                'success': False, 
                'verified': False,
                'message': 'Biometric verification required',
                'attendance_id': attendance.id
            })
            
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f'Error in verify_biometric: {str(e)}', exc_info=True)
        return JsonResponse({'success': False, 'error': 'Internal server error'}, status=500)

@login_required
def scan_qr_code(request, qr_code):
    if not request.user.is_student:
        return JsonResponse({'success': False, 'message': 'Access denied'})
    
    try:
        # First try to find by qr_code field directly
        try:
            # Try to parse as JSON first
            qr_data = json.loads(qr_code)
            if 'qr_id' in qr_data:
                qr = QRCode.objects.get(id=qr_data['qr_id'])
            else:
                return JsonResponse({'success': False, 'message': 'Invalid QR code format: missing qr_id'})
        except json.JSONDecodeError:
            # If not JSON, try to find by qr_code field directly
            qr = QRCode.objects.get(qr_code=qr_code)
        
        # Check if QR code is active
        if not qr.is_active:
            return JsonResponse({'success': False, 'message': 'This QR code is no longer active.'})
        
        # Check if QR code has expired
        if timezone.now() > qr.session_date + timezone.timedelta(minutes=qr.expiration_minutes):
            qr.is_active = False
            qr.save()
            return JsonResponse({'success': False, 'message': 'This QR code has expired.'})
        
        # Check if student is enrolled in the module
        if not qr.module.students.filter(id=request.user.id).exists():
            return JsonResponse({'success': False, 'message': 'You are not enrolled in this module.'})
        
        # Check if the student has already scanned this QR code
        if Attendance.objects.filter(student=request.user, qr_code=qr).exists():
            return JsonResponse({'success': False, 'message': 'You have already scanned this QR code.'})
        
        # Create attendance record
        Attendance.objects.create(
            student=request.user,
            qr_code=qr,
            timestamp=timezone.now(),
            status='present'
        )
        
        return JsonResponse({
            'success': True, 
            'message': 'Attendance recorded successfully.',
            'module': qr.module.code,
            'lecturer': qr.lecturer.get_full_name() or qr.lecturer.username,
            'session_date': qr.session_date.strftime('%Y-%m-%d %H:%M:%S')
        })
        
    except QRCode.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Invalid QR code. Please make sure you are scanning a valid code.'})
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid QR code format. Please scan a valid QR code.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'An error occurred: {str(e)}'})

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
def session_detail(request, qrcode_id):
    """View to display detailed information about a specific attendance session."""
    qrcode = get_object_or_404(QRCode, id=qrcode_id, lecturer=request.user)
    
    # Get attendance records for this QR code
    attendance_records = Attendance.objects.filter(qrcode=qrcode).select_related('student')
    
    # Calculate attendance statistics
    total_students = qrcode.module.students.count()
    present_count = attendance_records.filter(status='present').count()
    absent_count = total_students - present_count
    attendance_rate = (present_count / total_students * 100) if total_students > 0 else 0
    
    context = {
        'qrcode': qrcode,
        'attendance_records': attendance_records,
        'total_students': total_students,
        'present_count': present_count,
        'absent_count': absent_count,
        'attendance_rate': round(attendance_rate, 1)
    }
    
    return render(request, 'attendance/session_detail.html', context)

def download_attendance(request, qrcode_id):
    """View to download attendance data as Excel file."""
    import pandas as pd
    from io import BytesIO
    from django.http import HttpResponse
    from django.utils import timezone
    
    # Get the QR code and verify permissions
    qrcode = get_object_or_404(QRCode, id=qrcode_id, lecturer=request.user)
    
    # Get attendance records
    attendance_records = Attendance.objects.filter(qrcode=qrcode).select_related('student')
    
    # Create a DataFrame with the attendance data
    data = []
    for record in attendance_records:
        data.append({
            'Student ID': record.student.student_id,
            'Name': record.student.get_full_name() or record.student.username,
            'Status': record.get_status_display(),
            'Time': timezone.localtime(record.timestamp).strftime('%Y-%m-%d %H:%M:%S'),
            'Email': record.student.email
        })
    
    if not data:
        messages.warning(request, 'No attendance records found to export.')
        return redirect('attendance:session_detail', qrcode_id=qrcode_id)
    
    # Create Excel file in memory
    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Attendance', index=False)
        
        # Auto-adjust column widths
        worksheet = writer.sheets['Attendance']
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = (max_length + 2) * 1.2
            worksheet.column_dimensions[column_letter].width = adjusted_width
    
    # Prepare the response
    filename = f'attendance_{qrcode.module.code}_{qrcode.session_date}.xlsx'
    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response

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
