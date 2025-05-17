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
    """Lecturer dashboard view."""
    if not request.user.is_lecturer and not request.user.is_superuser:
        return redirect('attendance:login')
    
    user = request.user
    modules = Module.objects.filter(lecturers=user)
    
    # Get recent QR codes for this lecturer
    recent_qrcodes = QRCode.objects.filter(lecturer=user).order_by('-created_at')[:5]
    
    context = {
        'modules': modules,
        'recent_qrcodes': recent_qrcodes,
        'is_lecturer': True
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
def student_dashboard(request):
    """Student dashboard view with active QR codes and attendance statistics."""
    # Debug: Print user role information
    print(f"[DEBUG] User: {request.user.username}")
    print(f"[DEBUG] is_student: {request.user.is_student}")
    print(f"[DEBUG] is_lecturer: {request.user.is_lecturer}")
    print(f"[DEBUG] is_superuser: {request.user.is_superuser}")
    
    if not request.user.is_student and not request.user.is_superuser:
        print("[DEBUG] User is not a student, redirecting...")
        return redirect('attendance:login')
    
    user = request.user
    now = timezone.now()
    
    # Get all modules the student is enrolled in
    modules = Module.objects.filter(students=user).prefetch_related('qrcodes')
    
    # Get active QR codes for student's modules (active within the last 15 minutes or next 15 minutes)
    time_window = timezone.timedelta(minutes=15)
    active_qrcodes = QRCode.objects.filter(
        module__in=modules,
        is_active=True,
        session_date__gte=now - time_window,
        session_date__lte=now + time_window
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
        'modules': modules,
        'active_qrcodes': active_qrcodes,
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
