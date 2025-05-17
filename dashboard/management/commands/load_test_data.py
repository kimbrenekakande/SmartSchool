from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from attendance.models import Module, QRCode
from datetime import datetime, timedelta
import random
import string

def random_string(length=8):
    """Generate a random string of fixed length"""
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(length))

class Command(BaseCommand):
    help = 'Load test data into the database'

    def handle(self, *args, **options):
        User = get_user_model()
        
        # Create admin user if not exists
        admin, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@smartschool.com',
                'first_name': 'Admin',
                'last_name': 'User',
                'is_superuser': True,
                'is_staff': True,
                'is_lecturer': True,
            }
        )
        if created:
            admin.set_password('admin123')
            admin.save()
            self.stdout.write(self.style.SUCCESS('Created admin user'))
        
        # Create lecturer users
        lecturers = []
        for i in range(1, 4):
            lecturer, created = User.objects.get_or_create(
                username=f'lecturer{i}',
                defaults={
                    'email': f'lecturer{i}@smartschool.com',
                    'first_name': f'Lecturer',
                    'last_name': f'{i}',
                    'is_lecturer': True,
                }
            )
            if created:
                lecturer.set_password('password123')
                lecturer.save()
            lecturers.append(lecturer)
        self.stdout.write(self.style.SUCCESS('Created lecturer users'))
        
        # Create student users
        students = []
        for i in range(1, 51):
            student, created = User.objects.get_or_create(
                username=f'student{i}',
                defaults={
                    'email': f'student{i}@smartschool.com',
                    'first_name': f'Student',
                    'last_name': f'{i}',
                    'is_student': True,
                }
            )
            if created:
                student.set_password('password123')
                student.save()
            students.append(student)
        self.stdout.write(self.style.SUCCESS('Created student users'))
        
        # Create modules
        module_names = [
            'Mathematics', 'Physics', 'Chemistry', 'Biology', 'Computer Science',
            'English', 'History', 'Geography', 'Economics', 'Business Studies'
        ]
        
        modules = []
        for i, name in enumerate(module_names, 1):
            module, created = Module.objects.get_or_create(
                code=f'MOD{i:03d}',
                defaults={
                    'name': name,
                    'description': f'This is a test module for {name}'
                }
            )
            if created:
                # Assign 1-2 random lecturers to each module
                module_lecturers = random.sample(lecturers, random.randint(1, 2))
                module.lecturers.set(module_lecturers)
                module.save()
            modules.append(module)
        self.stdout.write(self.style.SUCCESS('Created modules'))
        
        # Create QR codes
        for module in modules:
            # Create active QR code
            QRCode.objects.create(
                module=module,
                lecturer=module.lecturers.first(),
                session_date=datetime.now(),
                qr_code=f'QR-{module.code}-{random_string(10)}',
                is_active=True,
                expiration_minutes=60
            )
            
            # Create some expired QR codes
            for _ in range(random.randint(1, 3)):
                QRCode.objects.create(
                    module=module,
                    lecturer=module.lecturers.first(),
                    session_date=datetime.now() - timedelta(days=random.randint(1, 30)),
                    qr_code=f'QR-{module.code}-{random_string(10)}',
                    is_active=False,
                    expiration_minutes=60
                )
        
        self.stdout.write(self.style.SUCCESS('Created QR codes'))
        self.stdout.write(self.style.SUCCESS('Test data loaded successfully!'))
        self.stdout.write('\nTest users:')
        self.stdout.write('Admin: username=admin, password=admin123')
        self.stdout.write('Lecturers: username=lecturer1-3, password=password123')
        self.stdout.write('Students: username=student1-50, password=password123')
