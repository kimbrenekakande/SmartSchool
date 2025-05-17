from django.urls import path
from . import views

app_name = 'attendance'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('generate/', views.generate_qr, name='generate_qr'),
    path('view/<int:qr_id>/', views.view_qr, name='view_qr'),
    path('attendance/<int:module_id>/<int:qr_id>/', views.attendance_detail, name='attendance_detail'),
    path('scan/', views.scan_qr, name='scan_qr'),
    path('deactivate/<int:qr_id>/', views.deactivate_qr, name='deactivate_qr'),
    path('extend/<int:qr_id>/', views.extend_qr_expiration, name='extend_qr'),
    path('qr-history/', views.qr_history, name='qr_history'),
    path('student/scan/', views.student_scan, name='student_scan'),
    path('scan/<str:qr_code>/', views.scan_qr_code, name='scan_qr_code'),
    path('attendance/<int:module_id>/', views.attendance_report, name='attendance_report'),
]
