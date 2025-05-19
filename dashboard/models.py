from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth import get_user_model
from attendance.models import Module

class ClassSchedule(models.Model):
    """
    Model to represent class schedule/timetable.
    Ensures no overlapping classes for the same module, lecturer, or room at the same time.
    """
    DAYS_OF_WEEK = [
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
    ]
    
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='schedules')
    lecturer = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, limit_choices_to={'is_lecturer': True})
    day_of_week = models.CharField(max_length=10, choices=DAYS_OF_WEEK)
    start_time = models.TimeField()
    end_time = models.TimeField()
    room = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['day_of_week', 'start_time']
        unique_together = [
            ['module', 'day_of_week', 'start_time'],  # Same module can't have multiple classes at same time
            ['lecturer', 'day_of_week', 'start_time'],  # Lecturer can't teach multiple classes at same time
            ['room', 'day_of_week', 'start_time'],  # Room can't be double-booked
        ]
    
    def __str__(self):
        return f"{self.module.name} - {self.get_day_of_week_display()} {self.start_time}-{self.end_time}"
    
    def clean(self):
        # Ensure end time is after start time
        if self.end_time <= self.start_time:
            raise ValidationError('End time must be after start time')
        
        # Check for overlapping classes (same day, overlapping times, same room/lecturer)
        overlapping = ClassSchedule.objects.filter(
            day_of_week=self.day_of_week,
            is_active=True,
            start_time__lt=self.end_time,
            end_time__gt=self.start_time,
        ).exclude(pk=self.pk)  # Exclude current instance for updates
        
        # Check for room conflicts
        if overlapping.filter(room=self.room).exists():
            raise ValidationError(f'Room {self.room} is already booked at this time')
            
        # Check for lecturer conflicts
        if overlapping.filter(lecturer=self.lecturer).exists():
            raise ValidationError(f'{self.lecturer.get_full_name()} is already teaching another class at this time')
    
    def save(self, *args, **kwargs):
        self.full_clean()  # Run validation before saving
        super().save(*args, **kwargs)
    
    @property
    def duration(self):
        """Calculate the duration of the class in minutes"""
        start = self.start_time.hour * 60 + self.start_time.minute
        end = self.end_time.hour * 60 + self.end_time.minute
        return end - start
    
    @classmethod
    def get_weekly_schedule(cls):
        """
        Get the complete weekly schedule organized by day
        Returns a dictionary with days as keys and lists of classes as values
        """
        schedule = {day[0]: [] for day in cls.DAYS_OF_WEEK}
        classes = cls.objects.filter(is_active=True).order_by('day_of_week', 'start_time')
        
        for class_schedule in classes:
            schedule[class_schedule.day_of_week].append(class_schedule)
            
        return schedule
