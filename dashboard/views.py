from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model, authenticate, login
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import qrcode
import qrcode.image.svg
from io import BytesIO
import uuid
from datetime import timedelta
from django.db.models import Count, F, Q, ExpressionWrapper, FloatField

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
    """Admin dashboard view with comprehensive statistics and analytics."""
    if not request.user.is_superuser:
        return redirect('attendance:login')
    
    # Basic counts with optimized queries
    total_modules = Module.objects.count()
    total_lecturers = User.objects.filter(is_lecturer=True).count()
    total_students = User.objects.filter(is_student=True).count()
    total_qr_codes = QRCode.objects.count()
    
    # Attendance statistics with optimized queries
    attendance_stats = Attendance.objects.aggregate(
        total=Count('id'),
        present=Count('id', filter=Q(status='present')),
        late=Count('id', filter=Q(status='late')),
        absent=Count('id', filter=Q(status='absent'))
    )
    
    total_attendance_records = attendance_stats['total']
    present_count = attendance_stats['present']
    late_count = attendance_stats['late']
    absent_count = attendance_stats['absent']
    
    attendance_rate = (present_count / total_attendance_records * 100) if total_attendance_records > 0 else 0
    
    # Module statistics with optimized queries
    modules = Module.objects.prefetch_related('qrcodes', 'students').all()
    module_stats = []
    
    # Get attendance data for all modules in a single query
    module_attendance = Attendance.objects.values('qrcode__module')\
        .annotate(
            total=Count('id'),
            present=Count('id', filter=Q(status='present')),
            sessions=Count('qrcode', distinct=True)
        )
    
    # Convert to dictionary for faster lookups
    attendance_by_module = {item['qrcode__module']: item for item in module_attendance}
    
    for module in modules:
        module_data = attendance_by_module.get(module.id, {'total': 0, 'present': 0, 'sessions': 0})
        total_sessions = module_data['sessions'] or 1  # Avoid division by zero
        module_attendance_rate = (module_data['present'] / (module_data['total'] or 1)) * 100
        
        module_stats.append({
            'id': module.id,
            'code': module.code,
            'name': module.name,
            'total_sessions': total_sessions,
            'attendance_rate': round(module_attendance_rate, 1),
            'enrolled_students': module.students.count(),
        })
    
    # Sort modules by attendance rate (descending) and get top 5
    module_stats = sorted(module_stats, key=lambda x: x['attendance_rate'], reverse=True)[:5]
    
    # Get recent QR codes with attendance data and related objects
    recent_qrcodes = QRCode.objects.select_related('module', 'lecturer')\
                                 .prefetch_related('attendance_set')\
                                 .order_by('-created_at')[:5]
    
    # Prepare data for charts - Last 30 days attendance trend
    today = timezone.now().date()
    date_range = [today - timezone.timedelta(days=i) for i in range(29, -1, -1)]
    
    # Get daily attendance data in a single query
    daily_data = Attendance.objects.filter(
        timestamp__date__gte=date_range[0],
        timestamp__date__lte=today
    ).values('timestamp__date').annotate(
        total=Count('id'),
        present=Count('id', filter=Q(status='present')),
        late=Count('id', filter=Q(status='late'))
    ).order_by('timestamp__date')
    
    # Create a dictionary of date to attendance data
    daily_attendance_dict = {
        item['timestamp__date']: {
            'total': item['total'],
            'present': item['present'],
            'rate': (item['present'] / item['total'] * 100) if item['total'] > 0 else 0
        } for item in daily_data
    }
    
    # Prepare data for the chart
    daily_attendance = []
    for date in date_range:
        if date in daily_attendance_dict:
            daily_attendance.append(round(daily_attendance_dict[date]['rate'], 1))
        else:
            daily_attendance.append(0)
    
    # Student attendance distribution with optimized query
    student_attendance = User.objects.filter(is_student=True)\
        .annotate(
            total_attendance=Count('attendance', filter=Q(attendance__status__in=['present', 'late', 'absent'])),
            present_attendance=Count('attendance', filter=Q(attendance__status='present'))
        )\
        .values('id', 'total_attendance', 'present_attendance')
    
    # Calculate distribution
    attendance_distribution = {
        '90-100%': 0,
        '75-89%': 0,
        '50-74%': 0,
        '0-49%': 0
    }
    
    for student in student_attendance:
        if student['total_attendance'] > 0:
            rate = (student['present_attendance'] / student['total_attendance']) * 100
            if rate >= 90:
                attendance_distribution['90-100%'] += 1
            elif rate >= 75:
                attendance_distribution['75-89%'] += 1
            elif rate >= 50:
                attendance_distribution['50-74%'] += 1
            else:
                attendance_distribution['0-49%'] += 1
    
    # Get module with highest and lowest attendance
    if module_stats:
        best_module = max(module_stats, key=lambda x: x['attendance_rate'])
        worst_module = min(module_stats, key=lambda x: x['attendance_rate'])
    else:
        best_module = worst_module = None
    
    # Get recent activity (last 5 attendance records)
    recent_activity = Attendance.objects.select_related('student', 'qrcode__module')\
                                     .order_by('-timestamp')[:5]
    
    context = {
        # Basic counts
        'total_modules': total_modules,
        'total_lecturers': total_lecturers,
        'total_students': total_students,
        'total_qr_codes': total_qr_codes,
        'total_attendance_records': total_attendance_records,
        'present_count': present_count,
        'late_count': late_count,
        'absent_count': absent_count,
        'attendance_rate': round(attendance_rate, 1),
        
        # Module statistics
        'module_stats': module_stats,
        'best_module': best_module,
        'worst_module': worst_module,
        'recent_qrcodes': recent_qrcodes,
        'recent_activity': recent_activity,
        
        # Chart data
        'date_labels': [date.strftime('%b %d') for date in date_range],
        'daily_attendance': daily_attendance,
        'attendance_distribution': attendance_distribution,
        'attendance_distribution_labels': list(attendance_distribution.keys()),
        'attendance_distribution_data': list(attendance_distribution.values()),
        
        # Current time for the dashboard
        'current_time': timezone.now(),
        'is_admin': True,
        
        # Additional stats
        'active_sessions': QRCode.objects.filter(is_active=True).count(),
        'today_attendance': Attendance.objects.filter(
            timestamp__date=today
        ).count()
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
            
            # Get the QR code object
            try:
                qr_code = QRCode.objects.get(id=qrcode_id, is_active=True)
            except QRCode.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Invalid or expired QR code'}, status=404)
            
            # Check if QR code is expired
            if qr_code.expiry_time < timezone.now():
                return JsonResponse({
                    'success': False, 
                    'error': 'This QR code has expired'
                }, status=400)
            
            # Check if the student is enrolled in the module
            if not qr_code.module.enrolled_students.filter(id=request.user.id).exists():
                return JsonResponse({
                    'success': False, 
                    'error': 'You are not enrolled in this module'
                }, status=403)
            
            # Record attendance if not already recorded
            attendance, created = Attendance.objects.get_or_create(
                student=request.user,
                qr_code=qr_code,
                defaults={'is_present': True}
            )
            
            if not created and not attendance.is_present:
                attendance.is_present = True
                attendance.save()
                
            return JsonResponse({
                'success': True,
                'message': 'Attendance recorded successfully',
                'module_name': qr_code.module.name,
                'lecturer': qr_code.lecturer.get_full_name() or qr_code.lecturer.username
            })
        
        except QRCode.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Invalid or expired QR code'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
@require_http_methods(["POST"])
def generate_qr_code(request):
    """Generate a new QR code for attendance."""
    try:
        data = json.loads(request.body)
        module_id = data.get('module_id')
        duration = int(data.get('duration', 5))  # Default to 5 minutes
        
        # Get the module
        module = get_object_or_404(Module, id=module_id, lecturer=request.user)
        
        # Create a new QR code
        qr_code = QRCode.objects.create(
            module=module,
            lecturer=request.user,
            expires_at=timezone.now() + timedelta(minutes=duration)
        )
        
        # Generate QR code data
        qr_data = {
            'id': str(qr_code.id),
            'module': module.code,
            'expires': qr_code.expires_at.isoformat(),
        }
        
        # Create QR code image
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(json.dumps(qr_data))
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Save image to bytes
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        qr_code_image = buffer.getvalue()
        
        # In a real app, you might want to save this to a file or storage
        # For now, we'll just return the data URL
        import base64
        qr_code_data_url = f"data:image/png;base64,{base64.b64encode(qr_code_image).decode('utf-8')}"
        
        return JsonResponse({
            'success': True,
            'qr_code_id': str(qr_code.id),
            'expires_at': qr_code.expires_at.isoformat(),
            'module_name': module.name,
            'qr_code_image': qr_code_data_url,
            'url': request.build_absolute_uri(reverse('dashboard:submit_attendance', args=[qr_code.id]))
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@login_required
@require_http_methods(["POST"])
def end_session(request, session_id):
    """End an active QR code session."""
    try:
        qr_code = get_object_or_404(QRCode, id=session_id, lecturer=request.user, is_active=True)
        qr_code.is_active = False
        qr_code.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Session ended successfully',
            'session_id': str(qr_code.id)
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@login_required
def get_active_sessions(request):
    """Get all active QR code sessions for the lecturer."""
    try:
        active_sessions = QRCode.objects.filter(
            lecturer=request.user,
            is_active=True,
            expires_at__gt=timezone.now()
        ).select_related('module').order_by('expires_at')
        
        sessions_data = [{
            'id': str(session.id),
            'module_name': session.module.name,
            'module_code': session.module.code,
            'expires_at': session.expires_at.isoformat(),
            'time_remaining': (session.expires_at - timezone.now()).total_seconds(),
            'url': request.build_absolute_uri(reverse('dashboard:submit_attendance', args=[session.id]))
        } for session in active_sessions]
        
        return JsonResponse({
            'success': True,
            'sessions': sessions_data
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@login_required
def get_attendance_stats(request):
    """Get attendance statistics for the lecturer's modules."""
    try:
        # Get modules taught by the lecturer
        modules = Module.objects.filter(lecturer=request.user)
        
        # Get attendance statistics for each module
        stats = []
        for module in modules:
            # Get total students enrolled
            total_students = module.enrolled_students.count()
            
            # Get attendance count for this module
            attendance_count = Attendance.objects.filter(
                qr_code__module=module,
                is_present=True
            ).values('student').distinct().count()
            
            # Calculate attendance percentage
            attendance_percentage = (attendance_count / total_students * 100) if total_students > 0 else 0
            
            stats.append({
                'module_id': module.id,
                'module_code': module.code,
                'module_name': module.name,
                'total_students': total_students,
                'attendance_count': attendance_count,
                'attendance_percentage': round(attendance_percentage, 2)
            })
        
        return JsonResponse({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
