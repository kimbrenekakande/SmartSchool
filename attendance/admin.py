from django.contrib import admin
from .models import Module, QRCode, Attendance

@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'attendance_threshold')
    search_fields = ('code', 'name')
    list_filter = ('attendance_threshold',)

@admin.register(QRCode)
class QRCodeAdmin(admin.ModelAdmin):
    list_display = ('module', 'lecturer', 'session_date', 'is_active')
    list_filter = ('module', 'lecturer', 'session_date', 'is_active')
    search_fields = ('module__code', 'lecturer__username', 'qr_code')
    date_hierarchy = 'session_date'

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'qrcode', 'timestamp', 'status')
    list_filter = ('status', 'qrcode__module', 'timestamp')
    search_fields = ('student__username', 'qrcode__qr_code')
    date_hierarchy = 'timestamp'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('student', 'qrcode__module')
