import os
import sys

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_auth.settings')
import django
django.setup()

def create_test_users():
    from django.contrib.auth import get_user_model
    from django.db import transaction
    
    User = get_user_model()
    
    # Create lecturer
    lecturer_data = {
        'username': 'lecturer1',
        'email': 'lecturer1@example.com',
        'password': 'lecturer123',
        'is_lecturer': True,
        'first_name': 'John',
        'last_name': 'Doe',
    }
    
    # Create students
    students_data = [
        {
            'username': 'student1',
            'email': 'student1@example.com',
            'password': 'student123',
            'is_student': True,
            'first_name': 'Alice',
            'last_name': 'Johnson',
        },
        {
            'username': 'student2',
            'email': 'student2@example.com',
            'password': 'student123',
            'is_student': True,
            'first_name': 'Bob',
            'last_name': 'Smith',
        },
        {
            'username': 'student3',
            'email': 'student3@example.com',
            'password': 'student123',
            'is_student': True,
            'first_name': 'Charlie',
            'last_name': 'Brown',
        }
    ]
    
    with transaction.atomic():
        # Create lecturer
        if not User.objects.filter(username=lecturer_data['username']).exists():
            lecturer = User.objects.create_user(
                username=lecturer_data['username'],
                email=lecturer_data['email'],
                password=lecturer_data['password'],
                is_lecturer=lecturer_data['is_lecturer'],
                first_name=lecturer_data['first_name'],
                last_name=lecturer_data['last_name']
            )
            print(f"Created lecturer: {lecturer.username} / {lecturer_data['password']}")
        else:
            lecturer = User.objects.get(username=lecturer_data['username'])
            print(f"Lecturer {lecturer.username} already exists")
        
        # Create students
        for student_data in students_data:
            if not User.objects.filter(username=student_data['username']).exists():
                student = User.objects.create_user(
                    username=student_data['username'],
                    email=student_data['email'],
                    password=student_data['password'],
                    is_student=student_data['is_student'],
                    first_name=student_data['first_name'],
                    last_name=student_data['last_name']
                )
                print(f"Created student: {student.username} / {student_data['password']}")
            else:
                student = User.objects.get(username=student_data['username'])
                print(f"Student {student.username} already exists")
    
    print("\nTest users have been created successfully!")

if __name__ == "__main__":
    print("Creating test users...")
    create_test_users()
    print("\nYou can now log in with the following accounts:")
    print("\nLecturer:")
    print("  Username: lecturer1")
    print("  Password: lecturer123")
    print("\nStudents:")
    print("  Username: student1 / student2 / student3")
    print("  Password: student123 (for all students)")
