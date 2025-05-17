from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
User = get_user_model()
from attendance.models import Module, QRCode, Attendance
from django.urls import reverse

@login_required
def redirect_to_dashboard(request):
    """Redirect user to their appropriate dashboard based on role."""
    user = request.user
    
    if user.is_superuser:
        return redirect('dashboard:admin_dashboard')
    elif user.is_lecturer:
        return redirect('dashboard:lecturer_dashboard')
    elif user.is_student:
        return redirect('dashboard:student_dashboard')
    else:
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
def student_dashboard(request):
    """Student dashboard view."""
    if not request.user.is_student:
        return redirect('attendance:login')
    
    user = request.user
    modules = Module.objects.filter(students=user)
    
    # Get attendance statistics
    attendance_stats = {}
    for module in modules:
        total_sessions = QRCode.objects.filter(module=module).count()
        attended = Attendance.objects.filter(
            student=user,
            qrcode__module=module,
            status='present'
        ).count()
        percentage = (attended / total_sessions * 100) if total_sessions > 0 else 0
        attendance_stats[module] = {
            'total_sessions': total_sessions,
            'attended': attended,
            'percentage': percentage
        }
    
    context = {
        'modules': modules,
        'attendance_stats': attendance_stats,
        'is_student': True
    }
    return render(request, 'dashboard/student.html', context)
