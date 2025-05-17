import os
import random
from datetime import datetime, timedelta
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_auth.settings')
django.setup()

from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
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
    print("Creating users...")
    # Create lecturers
    for name in lecturer_names:
        username = name.lower().replace(" ", "_").replace(".", "")
        User.objects.create(
            username=username,
            first_name=name.split()[1],
            last_name=name.split()[0],
            email=f"{username}@example.com",
            password=make_password("password123"),
            is_staff=True
        )
    
    # Create students
    for name in student_names:
        username = name.lower().replace(" ", "_").replace(".", "")
        User.objects.create(
            username=username,
            first_name=name.split()[1],
            last_name=name.split()[0],
            email=f"{username}@example.com",
            password=make_password("password123")
        )

def create_modules():
    print("Creating modules...")
    lecturers = User.objects.filter(is_staff=True)
    for module_name in dummy_modules:
        module = Module.objects.create(
            name=module_name,
            code=module_name.replace(" ", "_")[:10],
            attendance_threshold=75
        )
        # Add 1-3 lecturers to each module
        num_lecturers = random.randint(1, 3)
        module.lecturers.add(*random.sample(list(lecturers), num_lecturers))

def create_attendance_data():
    print("Creating attendance data...")
    modules = Module.objects.all()
    students = User.objects.filter(is_staff=False)
    
    # Create QR codes for each module for the last 30 days
    for module in modules:
        for day in range(30):
            date = datetime.now() - timedelta(days=day)
            qr_code = QRCode.objects.create(
                module=module,
                lecturer=choice(module.lecturers.all()),
                session_date=date
            )
            
            # Create attendance records for random students
            present_students = random.sample(list(students), randint(0, len(students)))
            for student in present_students:
                Attendance.objects.create(
                    student=student,
                    qrcode=qr_code,
                    status='present'
                )

def clear_existing_data():
    print("Clearing existing data...")
    User.objects.all().delete()
    Module.objects.all().delete()
    QRCode.objects.all().delete()
    Attendance.objects.all().delete()

def main():
    print("Starting dummy data generation...")
    clear_existing_data()
    create_users()
    create_modules()
    create_attendance_data()
    print("Dummy data generation complete!")

if __name__ == "__main__":
    main()
