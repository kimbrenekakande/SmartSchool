from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
User = get_user_model()
from attendance.models import Module, QRCode, Attendance
from django.urls import reverse

@login_required
def index(request):
    # If user is not authenticated, redirect to login
    if not request.user.is_authenticated:
        return redirect(reverse('attendance:login') + '?next=' + request.path)
    
    # If user is authenticated but doesn't have a role, redirect to login
    if not request.user.is_staff and not request.user.is_superuser:
        return redirect(reverse('attendance:login') + '?next=' + request.path)
    
    user = request.user
    
    if user.is_superuser:
        # Admin dashboard
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
    
    elif user.is_lecturer:
        # Lecturer dashboard
        modules = Module.objects.filter(lecturers=user)
        
        # Get recent QR codes for this lecturer
        recent_qrcodes = QRCode.objects.filter(lecturer=user).order_by('-created_at')[:5]
        
        context = {
            'modules': modules,
            'recent_qrcodes': recent_qrcodes,
            'is_lecturer': True
        }
        return render(request, 'dashboard/lecturer.html', context)
    
    elif user.is_student:
        # Student dashboard
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
    
    # If user doesn't have any role, redirect to login
    return redirect(reverse('attendance:login') + '?next=' + request.path)
