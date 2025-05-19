import qrcode
import json
from django.db import models
from django.contrib.auth import get_user_model
from django.conf import settings
from django.db.models import Count, Q, Avg
from django.utils import timezone
import qrcode
import json
from io import BytesIO
from django.core.files import File
import os
from datetime import timedelta
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import Distance
from django.core.exceptions import ValidationError
import hashlib
import base64
from django.core.files.base import ContentFile
from django.core.files import File
from io import BytesIO

# Use the custom user model
User = get_user_model()

class Module(models.Model):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    course_outline = models.TextField(blank=True, help_text='Detailed course outline, topics, and learning objectives')
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

    def has_overlapping_session(self):
        """Check if there's an overlapping session for this module within 3 hours."""
        # Calculate the time window (3 hours before and after the session)
        time_window_start = self.session_date - timezone.timedelta(hours=3)
        time_window_end = self.session_date + timezone.timedelta(hours=3)
        
        # Check for overlapping active QR codes for the same module
        overlapping_qrs = QRCode.objects.filter(
            module=self.module,
            is_active=True,
            session_date__range=(time_window_start, time_window_end)
        ).exclude(id=self.id)  # Exclude the current QR code
        
        return overlapping_qrs.exists()

class Attendance(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, limit_choices_to={'is_student': True})
    qrcode = models.ForeignKey(QRCode, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[
        ('present', 'Present'), 
        ('absent', 'Absent'),
        ('pending_verification', 'Pending Biometric Verification')
    ], default='pending_verification')
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    device_info = models.JSONField(null=True, blank=True)
    biometric_verified = models.BooleanField(default=False)
    biometric_data = models.TextField(null=True, blank=True)  # Store hashed biometric data
    verification_attempts = models.PositiveIntegerField(default=0)
    last_verification_attempt = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ('student', 'qrcode')
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['biometric_verified']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.qrcode.module.code} - {self.get_status_display()}"
    
    def clean(self):
        if self.biometric_verified and not self.biometric_data:
            raise ValidationError('Biometric data is required when verification is marked as complete.')
    
    def save(self, *args, **kwargs):
        # Set status based on location if coordinates are provided
        if self.latitude is not None and self.longitude is not None:
            self.status = self.check_location()
        
        # Hash biometric data before saving
        if self.biometric_data and not self.biometric_verified:
            self.biometric_data = self._hash_biometric_data(self.biometric_data)
        
        super().save(*args, **kwargs)
    
    def _hash_biometric_data(self, raw_data):
        """Hash the biometric data for secure storage"""
        if not raw_data:
            return None
        # Use a strong hashing algorithm (e.g., SHA-256)
        hasher = hashlib.sha256()
        hasher.update(raw_data.encode('utf-8'))
        return hasher.hexdigest()
    
    def verify_biometric(self, input_data):
        """Verify biometric data against stored hash"""
        if not self.biometric_data:
            return False
            
        # Hash the input and compare with stored hash
        input_hash = self._hash_biometric_data(input_data)
        return input_hash == self.biometric_data
    
    def check_location(self):
        """Check if student's location is within acceptable range of the class"""
        if not all([self.latitude, self.longitude]):
            return 'absent'
            
        # Get all attendance for this session
        session_attendance = Attendance.objects.filter(
            qrcode=self.qrcode,
            latitude__isnull=False,
            longitude__isnull=False
        ).exclude(id=self.id)
        
        if not session_attendance.exists():
            return 'present'  # First student is always within range
            
        # Get average location of other students
        avg_lat = session_attendance.aggregate(avg_lat=Avg('latitude'))['avg_lat']
        avg_lon = session_attendance.aggregate(avg_lon=Avg('longitude'))['avg_lon']
        
        if avg_lat is None or avg_lon is None:
            return 'present'
            
        # Calculate distance from average location (in meters)
        class_location = Point(float(avg_lon), float(avg_lat))
        student_location = Point(float(self.longitude), float(self.latitude))
        distance = class_location.distance(student_location) * 100  # Convert to meters
        
        # If within 50 meters of the class location
        return 'present' if distance <= 50 else 'absent'

@receiver(post_save, sender=QRCode)
def generate_qr_code(sender, instance, created, **kwargs):
    if created:
        # Generate a unique QR code
        instance.qr_code = f"QR-{instance.module.code}-{instance.session_date.strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
        instance.save()
