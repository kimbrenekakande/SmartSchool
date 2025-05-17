import qrcode
import json
from django.db import models
from django.contrib.auth import get_user_model
from django.conf import settings
from django.utils import timezone
import uuid
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.files.base import ContentFile
from django.core.files import File
from io import BytesIO

# Use the custom user model
User = get_user_model()

class Module(models.Model):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    lecturers = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='modules', limit_choices_to={'is_lecturer': True})
    students = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='enrolled_modules', limit_choices_to={'is_student': True})
    attendance_threshold = models.DecimalField(max_digits=5, decimal_places=2, default=75.00)

    def __str__(self):
        return f"{self.code} - {self.name}"

class QRCode(models.Model):
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='qrcodes')
    lecturer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, limit_choices_to={'is_lecturer': True})
    session_date = models.DateTimeField()
    qr_code = models.CharField(max_length=255, unique=True)
    qr_image = models.ImageField(upload_to='qr_codes/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    expiration_minutes = models.PositiveIntegerField(default=60)  # QR code validity in minutes
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"QR Code for {self.module.code} - {self.session_date}"

    def save(self, *args, **kwargs):
        if not self.qr_code:
            self.qr_code = f"{self.module.code}_{self.lecturer.username}_{self.session_date.strftime('%Y%m%d%H%M%S')}"
        super().save(*args, **kwargs)

    def generate_qr_image(self):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        # Add more data to QR code
        qr_data = {
            'module_code': self.module.code,
            'session_date': self.session_date.isoformat(),
            'lecturer': self.lecturer.username,
            'qr_id': self.id
        }
        qr.add_data(json.dumps(qr_data))
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        self.qr_image.save(f'qr_{self.id}.png', ContentFile(buffer.getvalue()), save=False)

    def get_attendance_percentage(self):
        if not self.module.students.exists():
            return 0
        attended = self.attendance_set.count()
        total = self.module.students.count()
        return (attended / total) * 100

    def get_status(self):
        if not self.is_active:
            return 'Deactivated'
        if timezone.now() > self.session_date:
            return 'Expired'
        return 'Active'

    def deactivate(self):
        self.is_active = False
        self.save()

    def extend_expiration(self, minutes):
        self.expiration_minutes += minutes
        self.session_date = timezone.now() + timezone.timedelta(minutes=self.expiration_minutes)
        self.save()

    def get_expiration_time(self):
        return self.session_date.strftime('%Y-%m-%d %H:%M:%S')

    def get_remaining_minutes(self):
        """Return the number of minutes remaining until the QR code expires."""
        if not self.is_active:
            return 0
        now = timezone.now()
        if now > self.session_date:
            return 0
        return (self.session_date - now).total_seconds() // 60

    def get_remaining_time(self):
        """Return a user-friendly string of the remaining time."""
        if not self.is_active:
            return 'Deactivated'
            
        now = timezone.now()
        if now > self.session_date:
            return 'Expired'
            
        delta = self.session_date - now
        minutes = delta.total_seconds() // 60
        
        if minutes < 1:
            return 'Less than a minute'
        elif minutes < 60:
            return f'{int(minutes)}m'
        else:
            hours = minutes // 60
            remaining_minutes = int(minutes % 60)
            return f'{int(hours)}h {remaining_minutes}m'
        remaining = self.session_date - timezone.now()
        return str(remaining).split('.')[0]  # Remove microseconds

class Attendance(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, limit_choices_to={'is_student': True})
    qrcode = models.ForeignKey(QRCode, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[('present', 'Present'), ('absent', 'Absent')])
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    device_info = models.JSONField(null=True, blank=True)
    
    class Meta:
        unique_together = ('student', 'qrcode')
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.student.username} - {self.qrcode} - {self.status}"
        
    def save(self, *args, **kwargs):
        # Add device info if available
        if not self.device_info:
            self.device_info = {
                'user_agent': '',  # Will be set in the view
                'ip_address': ''   # Will be set in the view
            }
        super().save(*args, **kwargs)

@receiver(post_save, sender=QRCode)
def generate_qr_code(sender, instance, created, **kwargs):
    if created:
        # Generate a unique QR code
        instance.qr_code = f"QR-{instance.module.code}-{instance.session_date.strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
        instance.save()
