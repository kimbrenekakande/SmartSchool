import os
import random
from datetime import datetime, timedelta
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SmartSchool.settings')
django.setup()

from django.contrib.auth import get_user_model
from attendance.models import Module, QRCode, Attendance
from random import choice, randint

# Sample data
dummy_modules = [
    "Computer Science 101",
    "Mathematics for Computing",
    "Introduction to Programming",
    "Web Development",
    "Database Systems",
    "Data Structures and Algorithms",
    "Operating Systems",
    "Networks and Security",
    "Software Engineering",
    "Artificial Intelligence"
]

student_names = [
    "John Smith", "Sarah Johnson", "Michael Brown", "Emily Davis",
    "David Wilson", "Emma Taylor", "Daniel Anderson", "Olivia Martinez",
    "James Thompson", "Sophia White", "Robert Garcia", "Ava Rodriguez",
    "William Martinez", "Isabella Wilson", "Joseph Taylor", "Mia Anderson"
]

lecturer_names = [
    "Dr. John Williams", "Prof. Sarah Wilson", "Dr. Michael Brown",
    "Prof. Emily Davis", "Dr. David Johnson", "Prof. Sarah Thompson",
    "Dr. Michael Anderson", "Prof. Emily Martinez"
]

def create_users():
    """Create dummy users - lecturers and students"""
    print("Creating users...")
    
    # Create admin user
    User = get_user_model()
    admin = User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='admin123'
    )
    
    # Create lecturers
    for name in lecturer_names:
        username = name.lower().replace(' ', '_')
        user = User.objects.create_user(
            username=username,
            email=f'{username}@example.com',
            password='lecturer123',
            first_name=name.split()[1],
            last_name=name.split()[2] if len(name.split()) > 2 else '',
            is_lecturer=True,
            is_staff=True
        )
        print(f"Created lecturer: {name}")
    
    # Create students
    for name in student_names:
        username = name.lower().replace(' ', '_')
        user = User.objects.create_user(
            username=username,
            email=f'{username}@example.com',
            password='student123',
            first_name=name.split()[0],
            last_name=name.split()[1],
            is_student=True
        )
        print(f"Created student: {name}")

def create_modules():
    """Create dummy modules and assign lecturers"""
    print("\nCreating modules...")
    User = get_user_model()
    lecturers = User.objects.filter(is_lecturer=True)
    
    for module_name in dummy_modules:
        module = Module.objects.create(
            code=module_name.replace(" ", "_")[:10],
            name=module_name,
            description=f"Description for {module_name}",
            attendance_threshold=75.00
        )
        
        # Assign 1-3 lecturers to each module
        num_lecturers = random.randint(1, 3)
        module.lecturers.add(*random.sample(list(lecturers), num_lecturers))
        print(f"Created module: {module_name}")

def create_student_enrollments():
    """Enroll students in modules"""
    print("\nEnrolling students in modules...")
    User = get_user_model()
    students = User.objects.filter(is_student=True)
    modules = Module.objects.all()
    
    for student in students:
        # Enroll each student in 3-5 random modules
        num_modules = random.randint(3, 5)
        modules_to_enroll = random.sample(list(modules), num_modules)
        for module in modules_to_enroll:
            module.students.add(student)
            print(f"Enrolled {student.username} in {module.name}")

def create_qr_codes():
    """Create dummy QR codes for attendance"""
    print("\nCreating QR codes...")
    modules = Module.objects.all()
    
    # Create QR codes for each module
    for module in modules:
        # Create 5-10 QR codes per module
        num_qrcodes = random.randint(5, 10)
        for i in range(num_qrcodes):
            qr = QRCode.objects.create(
                module=module,
                lecturer=random.choice(module.lecturers.all()),
                session_date=datetime.now() + timedelta(days=random.randint(1, 30)),
                is_active=True
            )
            print(f"Created QR code for {module.code}")

def create_attendance_records():
    """Create dummy attendance records"""
    print("\nCreating attendance records...")
    qrcodes = QRCode.objects.all()
    
    for qr in qrcodes:
        # Create attendance records for enrolled students
        for student in qr.module.students.all():
            # Randomly decide if student attended (70% chance)
            if random.random() < 0.7:
                Attendance.objects.create(
                    student=student,
                    qr_code=qr,
                    status='present'
                )
        print(f"Created attendance records for QR code {qr.id}")

def main():
    print("Starting dummy data creation...")
    create_users()
    create_modules()
    create_student_enrollments()
    create_qr_codes()
    create_attendance_records()
    print("\nDummy data creation completed!")
    print("\nYou can now log in with these credentials:")
    print("Admin: admin@example.com / admin123")
    print("\nLecturers: (username/password)")
    for name in lecturer_names:
        username = name.lower().replace(' ', '_')
        print(f"  {username} / lecturer123")
    print("\nStudents: (username/password)")
    for name in student_names:
        username = name.lower().replace(' ', '_')
        print(f"  {username} / student123")

if __name__ == '__main__':
    main()
