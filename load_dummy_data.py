import os
import sys
import random
from datetime import datetime, timedelta, time
from django.utils import timezone

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_auth.settings')
import django
django.setup()

def create_dummy_data():
    from django.contrib.auth import get_user_model
    from attendance.models import Module, QRCode, Attendance
    from dashboard.models import ClassSchedule
    
    User = get_user_model()
    
    print("Creating dummy data...")
    
    # Create users if they don't exist
    lecturer = User.objects.get_or_create(
        username='lecturer1',
        defaults={
            'email': 'lecturer1@example.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'is_lecturer': True
        }
    )[0]
    lecturer.set_password('lecturer123')
    lecturer.save()
    
    students = []
    for i in range(1, 6):
        student = User.objects.get_or_create(
            username=f'student{i}',
            defaults={
                'email': f'student{i}@example.com',
                'first_name': f'Student{i}',
                'last_name': f'Lastname{i}',
                'is_student': True
            }
        )[0]
        student.set_password('student123')
        student.save()
        students.append(student)
    
    print(f"Created {len(students)} students and 1 lecturer")
    
    # Create modules
    modules_data = [
        {
            'code': 'CS101',
            'name': 'Introduction to Computer Science',
            'description': 'Basic concepts of computer science and programming.',
            'lecturer': lecturer,
            'room': 'CS-101',
            'students': students[:3],  # First 3 students
        },
        {
            'code': 'MATH201',
            'name': 'Discrete Mathematics',
            'description': 'Mathematical structures that are fundamentally discrete.',
            'lecturer': lecturer,
            'room': 'MATH-201',
            'students': students[2:],  # Last 3 students (overlap of 1 student)
        },
        {
            'code': 'WEB301',
            'name': 'Web Development',
            'description': 'Introduction to modern web development.',
            'lecturer': lecturer,
            'room': 'WEB-301',
            'students': students,  # All students
        },
    ]
    
    modules = []
    for data in modules_data:
        module = Module.objects.create(
            code=data['code'],
            name=data['name'],
            description=data['description'],
            lecturer=data['lecturer'],
            room=data['room']
        )
        module.students.set(data['students'])
        modules.append(module)
        print(f"Created module: {module.code} - {module.name}")
    
    # Create class schedules
    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
    times = [
        ('09:00', '11:00'),
        ('11:00', '13:00'),
        ('14:00', '16:00'),
    ]
    
    for i, module in enumerate(modules):
        day = days[i % len(days)]
        start_time, end_time = times[i % len(times)]
        
        schedule = ClassSchedule.objects.create(
            module=module,
            day=day,
            start_time=start_time,
            end_time=end_time
        )
        print(f"Created schedule for {module.code}: {day} {start_time}-{end_time}")
    
    # Create QR codes and attendance records
    now = timezone.now()
    for module in modules:
        # Create a past QR code (1 week ago)
        past_qr = QRCode.objects.create(
            module=module,
            expires_at=now - timedelta(days=6, hours=1),  # Expired 1 day after creation
            is_active=False
        )
        
        # Create attendance records for the past QR code
        for student in module.students.all():
            # Randomly mark some students as present, some as absent
            status = 'present' if random.random() > 0.3 else 'absent'
            
            Attendance.objects.create(
                student=student,
                qrcode=past_qr,
                status=status,
                timestamp=now - timedelta(days=7, hours=2)  # 2 hours after QR code creation
            )
        
        # Create a current QR code
        current_qr = QRCode.objects.create(
            module=module,
            expires_at=now + timedelta(hours=1),  # Expires in 1 hour
            is_active=True
        )
        print(f"Created QR codes for {module.code}")
    
    print("\nDummy data created successfully!")
    print("\nYou can now log in with the following accounts:")
    print("\nLecturer:")
    print(f"  Username: {lecturer.username}")
    print("  Password: lecturer123")
    print("\nStudents:")
    for i, student in enumerate(students, 1):
        print(f"  Student {i}: {student.username} / student123")
    
    print("\nAdmin:")
    print("  URL: http://127.0.0.1:8000/admin/")
    print("  Username: admin")
    print("  Password: admin")

if __name__ == "__main__":
    create_dummy_data()
