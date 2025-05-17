from django.urls import path
from . import views
from django.contrib.auth.decorators import login_required

app_name = 'dashboard'

urlpatterns = [
    # Redirect root to appropriate dashboard
    path('', views.redirect_to_dashboard, name='index'),
    
    # Student dashboard
    path('student/', views.student_dashboard, name='student_dashboard'),
    
    # Lecturer dashboard
    path('lecturer/', views.lecturer_dashboard, name='lecturer_dashboard'),
    
    # Admin dashboard
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    
    # Legacy URL for backward compatibility
    path('dashboard/', views.redirect_to_dashboard, name='dashboard'),
]
