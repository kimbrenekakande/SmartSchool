from django.urls import path, re_path
from . import views
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
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
]
