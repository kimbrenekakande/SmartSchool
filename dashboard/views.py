from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model, authenticate, login
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

User = get_user_model()
from attendance.models import Module, QRCode, Attendance
from django.urls import reverse

@login_required
def redirect_to_dashboard(request):
    """Redirect user to their appropriate dashboard based on role."""
    user = request.user
    
    # Debug information
    print("\n=== DEBUG: REDIRECT TO DASHBOARD ===")
    print(f"User: {user.username}")
    print(f"is_superuser: {user.is_superuser}")
    print(f"is_lecturer: {user.is_lecturer}")
    print(f"is_student: {user.is_student}")
    print(f"is_staff: {user.is_staff}")
    print("=================================\n")
    
    # Check if user is a superuser first
    if user.is_superuser:
        print("Redirecting to admin dashboard")
        return redirect('dashboard:admin_dashboard')
    
    # Then check if user is a lecturer
    if user.is_lecturer:
        print("Redirecting to lecturer dashboard")
        return redirect('dashboard:lecturer_dashboard')
    
    # Then check if user is a student
    if user.is_student:
        print("Redirecting to student dashboard")
        return redirect('dashboard:student_dashboard')
    
    # If none of the above, redirect to login
    print("No valid role found, redirecting to login")
    return redirect('attendance:login')

@login_required
def admin_dashboard(request):
    """Admin dashboard view."""
    if not request.user.is_superuser:
        return redirect('attendance:login')
    
    total_modules = Module.objects.count()
    total_lecturers = User.objects.filter(is_lecturer=True).count()
    total_students = User.objects.filter(is_student=True).count()
    
    # Get recent QR codes
    recent_qrcodes = QRCode.objects.order_by('-created_at')[:5]
    
    context = {
        'total_modules': total_modules,
        'total_lecturers': total_lecturers,
        'total_students': total_students,
        'recent_qrcodes': recent_qrcodes,
        'is_admin': True
    }
    return render(request, 'dashboard/admin.html', context)

@login_required
def lecturer_dashboard(request):
    """Lecturer dashboard view with comprehensive statistics and attendance data."""
    if not request.user.is_lecturer and not request.user.is_superuser:
        return redirect('attendance:login')
    
    user = request.user
    now = timezone.now()
    
    # Get modules taught by this lecturer
    modules = Module.objects.filter(lecturers=user).prefetch_related('students')
    
    # Get active QR codes for this lecturer
    active_qrcodes = QRCode.objects.filter(
        lecturer=user,
        is_active=True
    ).select_related('module').order_by('-created_at')
    
    # Get recent QR codes for this lecturer
    recent_qrcodes = QRCode.objects.filter(lecturer=user).select_related('module').order_by('-created_at')[:5]
    
    # Calculate statistics
    total_students = sum(module.students.count() for module in modules)
    
    # Filter active sessions by checking expiration time
    active_sessions = []
    for qr in active_qrcodes:
        expiration_time = qr.created_at + timezone.timedelta(minutes=qr.expiration_minutes)
        if expiration_time > now:
            active_sessions.append(qr)
    
    active_sessions_count = len(active_sessions)
    
    # Get attendance statistics for recent sessions
    attendance_stats = []
    for qrcode in recent_qrcodes:
        total_attendance = Attendance.objects.filter(qrcode=qrcode).count()
        present_count = Attendance.objects.filter(qrcode=qrcode, status='present').count()
        attendance_rate = (present_count / total_attendance * 100) if total_attendance > 0 else 0
        
        attendance_stats.append({
            'qrcode': qrcode,
            'total_attendance': total_attendance,
            'present_count': present_count,
            'attendance_rate': round(attendance_rate, 1)
        })
    
    # Get upcoming sessions (next 7 days)
    upcoming_sessions = QRCode.objects.filter(
        lecturer=user,
        session_date__gte=now,
        session_date__lte=now + timezone.timedelta(days=7)
    ).order_by('session_date')[:5]
    
    # Calculate average attendance rate
    if attendance_stats:
        avg_attendance_rate = sum(stat['attendance_rate'] for stat in attendance_stats) / len(attendance_stats)
    else:
        avg_attendance_rate = 0
    
    context = {
        'modules': modules,
        'recent_qrcodes': recent_qrcodes,
        'upcoming_sessions': upcoming_sessions,
        'attendance_stats': attendance_stats,
        'total_students': total_students,
        'active_sessions': active_sessions_count,
        'active_qrcodes': active_sessions,  # Add active QR codes to context
        'module_count': modules.count(),
        'is_lecturer': True,
        'now': now,
        'avg_attendance_rate': round(avg_attendance_rate, 1)
    }
    return render(request, 'dashboard/lecturer.html', context)

@login_required
def debug_user_roles(request):
    """Debug view to check user roles"""
    user = request.user
    return JsonResponse({
        'username': user.username,
        'is_authenticated': user.is_authenticated,
        'is_staff': user.is_staff,
        'is_superuser': user.is_superuser,
        'is_lecturer': user.is_lecturer,
        'is_student': user.is_student,
        'groups': list(user.groups.values_list('name', flat=True)),
        'permissions': list(user.get_all_permissions()),
    })

@login_required
def enroll_in_module(request, module_id):
    """Handle module enrollment for students."""
    if not request.user.is_student and not request.user.is_superuser:
        messages.error(request, 'Only students can enroll in modules.')
        return redirect('dashboard:student_dashboard')
    
    module = get_object_or_404(Module, id=module_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'enroll':
            if not module.students.filter(id=request.user.id).exists():
                module.students.add(request.user)
                messages.success(request, f'Successfully enrolled in {module.code} - {module.name}')
            else:
                messages.info(request, f'You are already enrolled in {module.code}')
        elif action == 'unenroll':
            if module.students.filter(id=request.user.id).exists():
                module.students.remove(request.user)
                messages.success(request, f'Successfully unenrolled from {module.code} - {module.name}')
            else:
                messages.info(request, f'You are not enrolled in {module.code}')
    
    return redirect('dashboard:student_dashboard')

@login_required
def student_dashboard(request):
    """Student dashboard view with active QR codes and attendance statistics."""
    if not request.user.is_student and not request.user.is_superuser:
        return redirect('attendance:login')
    
    user = request.user
    now = timezone.now()
    
    # Get all modules the student is enrolled in
    enrolled_modules = Module.objects.filter(students=user).prefetch_related('qrcodes')
    
    # Get all available modules that the student is not enrolled in
    available_modules = Module.objects.exclude(students=user).order_by('code')
    
    # For backward compatibility
    modules = enrolled_modules
    
    # Get active QR codes for student's modules (active within the last 15 minutes or next 15 minutes)
    time_window = timezone.timedelta(minutes=15)
    active_qrcodes = QRCode.objects.filter(
        module__in=modules,
        is_active=True,
        session_date__gte=now - time_window,
        session_date__lte=now + time_window
    ).select_related('module', 'lecturer').order_by('session_date')
    
    # Get upcoming QR codes (next 24 hours)
    upcoming_qrcodes = QRCode.objects.filter(
        module__in=modules,
        is_active=True,
        session_date__gt=now,
        session_date__lte=now + timezone.timedelta(hours=24)
    ).select_related('module', 'lecturer').order_by('session_date')
    
    # Get attendance statistics for each module
    attendance_stats = {}
    total_percentage = 0
    module_count = 0
    total_attended = 0
    next_sessions = []
    
    for module in modules:
        # Get all QR codes for this module
        qr_codes = module.qrcodes.all()
        total_sessions = qr_codes.count()
        
        # Get attendance for this student and module
        attended = Attendance.objects.filter(
            student=user,
            qrcode__in=qr_codes,
            status='present'
        ).count()
        
        total_attended += attended
        
        # Calculate percentage (handle division by zero)
        percentage = (attended / total_sessions * 100) if total_sessions > 0 else 0
        
        # Update total percentage for overall calculation
        if total_sessions > 0:  # Only include modules with sessions
            total_percentage += percentage
            module_count += 1
        
        # Get next session (if any)
        next_session = qr_codes.filter(
            session_date__gte=now,
            is_active=True
        ).order_by('session_date').first()
        
        if next_session and next_session.session_date:
            next_sessions.append(next_session.session_date)
        
        attendance_stats[module] = {
            'total_sessions': total_sessions,
            'attended': attended,
            'percentage': round(percentage, 1),  # Round to 1 decimal place
            'next_session': next_session.session_date if next_session else None
        }
    
    # Calculate overall attendance percentage
    overall_attendance = round(total_percentage / module_count, 1) if module_count > 0 else 0
    
    # Get recent attendance records for the student
    recent_attendance = Attendance.objects.filter(
        student=user
    ).select_related('qrcode', 'qrcode__module').order_by('-timestamp')[:5]
    
    # Get the next upcoming session
    next_session = min(next_sessions) if next_sessions else None
    
    context = {
        'modules': enrolled_modules,
        'available_modules': available_modules,
        'active_qrcodes': active_qrcodes,
        'upcoming_qrcodes': upcoming_qrcodes,
        'attendance_stats': attendance_stats,
        'overall_attendance': overall_attendance,
        'total_attended': total_attended,
        'next_session': next_session,
        'recent_attendance': recent_attendance,
        'is_student': True,
        'now': now,
        'time_window': time_window
    }
    return render(request, 'dashboard/student.html', context)

@csrf_exempt
@login_required
def submit_attendance(request, qrcode_id):
    """Handle QR code submission with authentication."""
    if not request.user.is_student:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            password = data.get('password')
            latitude = data.get('latitude')
            longitude = data.get('longitude')
            
            # Verify password
            user = authenticate(username=request.user.username, password=password)
            if user is None:
                return JsonResponse({'status': 'error', 'message': 'Invalid password'}, status=400)
            
            # Get QR code
            qrcode = get_object_or_404(QRCode, id=qrcode_id, is_active=True)
            now = timezone.now()
            
            # Check if QR code is still valid
            if now > qrcode.session_date + timezone.timedelta(minutes=15):
                return JsonResponse({'status': 'error', 'message': 'QR code has expired'}, status=400)
            
            # Check if student is enrolled in the module
            if not qrcode.module.students.filter(id=user.id).exists():
                return JsonResponse({'status': 'error', 'message': 'Not enrolled in this module'}, status=400)
            
            # Record attendance
            attendance, created = Attendance.objects.get_or_create(
                student=user,
                qrcode=qrcode,
                defaults={
                    'status': 'present',
                    'latitude': latitude,
                    'longitude': longitude
                }
            )
            
            if not created:
                return JsonResponse({'status': 'error', 'message': 'Attendance already recorded'}, status=400)
                
            return JsonResponse({
                'status': 'success', 
                'message': 'Attendance recorded successfully',
                'module': qrcode.module.code,
                'session_date': qrcode.session_date
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)
