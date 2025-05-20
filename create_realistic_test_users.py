import os
import random
from datetime import datetime, timedelta

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_auth.settings')
import django
django.setup()

def create_test_users():
    from django.contrib.auth import get_user_model
    from django.db import transaction
    
    User = get_user_model()
    
    # List of realistic first and last names
    first_names = [
        'James', 'Mary', 'John', 'Patricia', 'Robert', 'Jennifer', 'Michael', 'Linda',
        'William', 'Elizabeth', 'David', 'Susan', 'Richard', 'Jessica', 'Joseph', 'Sarah',
        'Thomas', 'Karen', 'Charles', 'Nancy', 'Christopher', 'Lisa', 'Daniel', 'Betty',
        'Matthew', 'Margaret', 'Anthony', 'Sandra', 'Donald', 'Ashley', 'Mark', 'Kimberly'
    ]
    
    last_names = [
        'Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis',
        'Rodriguez', 'Martinez', 'Hernandez', 'Lopez', 'Gonzalez', 'Wilson', 'Anderson',
        'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin', 'Lee', 'Perez', 'Thompson',
        'White', 'Harris', 'Sanchez', 'Clark', 'Ramirez', 'Lewis', 'Robinson', 'Walker'
    ]
    
    # Create admin user if not exists
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@school.edu', 'admin123')
        print("Created admin user: admin / admin123")
    
    # Create 5 lecturers
    lecturers = []
    for i in range(1, 6):
        first = random.choice(first_names)
        last = random.choice(last_names)
        username = f"{first[0].lower()}{last.lower()}{i}"
        email = f"{username}@school.edu"
        
        lecturer = User.objects.create_user(
            username=username,
            email=email,
            first_name=first,
            last_name=last,
            is_lecturer=True
        )
        lecturer.set_password('lecturer123')
        lecturer.save()
        lecturers.append(lecturer)
        print(f"Created lecturer: {username} / lecturer123")
    
    # Create 30 students
    students = []
    for i in range(1, 31):
        first = random.choice(first_names)
        last = random.choice(last_names)
        username = f"s{str(i).zfill(3)}{last[0].lower()}"
        email = f"{username}@student.school.edu"
        
        student = User.objects.create_user(
            username=username,
            email=email,
            first_name=first,
            last_name=last,
            is_student=True
        )
        student.set_password('student123')
        student.save()
        students.append(student)
        print(f"Created student: {username} / student123")
    
    print("\nTest users created successfully!")
    print("\nAdmin:")
    print("  Username: admin")
    print("  Password: admin123")
    
    print("\nSample Lecturers:")
    for i, lecturer in enumerate(lecturers[:3], 1):
        print(f"  {i}. Username: {lecturer.username}")
        print(f"     Password: lecturer123")
        print(f"     Name: {lecturer.get_full_name()}")
    
    print("\nSample Students:")
    for i, student in enumerate(students[:5], 1):
        print(f"  {i}. Username: {student.username}")
        print(f"     Password: student123")
        print(f"     Name: {student.get_full_name()}")
    
    print("\nTotal users created:")
    print(f"- Admin: 1")
    print(f"- Lecturers: {len(lecturers)}")
    print(f"- Students: {len(students)}")

if __name__ == "__main__":
    print("Creating test users...\n")
    create_test_users()
