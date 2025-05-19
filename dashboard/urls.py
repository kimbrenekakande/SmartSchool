from django.urls import path, re_path
from . import views
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.views.generic import RedirectView

app_name = 'dashboard'

urlpatterns = [
    # Redirect root to appropriate dashboard
    path('', views.redirect_to_dashboard, name='index'),
    
    # Student dashboard (handle with and without trailing slash)
    path('student/', views.student_dashboard, name='student_dashboard'),
    re_path(r'^student$', RedirectView.as_view(url='/dashboard/student/', permanent=True)),
    
    # Lecturer dashboard
    path('lecturer/', views.lecturer_dashboard, name='lecturer_dashboard'),
    re_path(r'^lecturer$', RedirectView.as_view(url='/dashboard/lecturer/', permanent=True)),
    
    # Admin dashboard
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    re_path(r'^admin-dashboard$', RedirectView.as_view(url='/dashboard/admin-dashboard/', permanent=True)),
    
    # Legacy URL for backward compatibility
    path('dashboard/', views.redirect_to_dashboard, name='dashboard'),
    
    # Debug URL
    path('debug/roles/', views.debug_user_roles, name='debug_roles'),
    
    # Attendance submission
    path('submit-attendance/<int:qrcode_id>/', csrf_exempt(views.submit_attendance), name='submit_attendance'),
    
    # Module enrollment
    path('enroll/<int:module_id>/', login_required(views.enroll_in_module), name='enroll_module'),
    
    # Lecturer API endpoints
    path('attendance-stats/', login_required(views.get_attendance_stats), name='attendance_stats'),
    path('schedule/', login_required(views.view_schedule), name='view_schedule'),
    path('module/<int:module_id>/', login_required(views.module_detail), name='module_detail'),
    path('get-active-sessions/', login_required(views.get_active_sessions), name='get_active_sessions'),
    path('api/lecturer/generate-qr/', login_required(views.generate_qr_code), name='generate_qr_code'),
    path('api/lecturer/end-session/<uuid:session_id>/', login_required(views.end_session), name='end_session'),
    path('api/lecturer/active-sessions/', login_required(views.get_active_sessions), name='get_active_sessions'),
    path('api/lecturer/attendance-stats/', login_required(views.get_attendance_stats), name='get_attendance_stats'),
]
