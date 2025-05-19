from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from attendance.models import Module, QRCode, Attendance
from dashboard.models import ClassSchedule
from datetime import datetime, timedelta, time
import random
import string
from django.utils import timezone

def random_string(length=8):
    """Generate a random string of fixed length"""
    letters = string.ascii_letters
    return ''.join(random.choice(letters) for i in range(length))

class Command(BaseCommand):
    help = 'Load test data into the database'

    def create_sample_modules(self, lecturer, students):
        """Create sample modules with course outlines"""
        modules = []
        
        module_data = [
            {
                'code': 'CS101',
                'name': 'Introduction to Computer Science',
                'description': 'Basic concepts of computer science and programming.',
                'outline': (
                    '## Course Outline\n\n'
                    '1. Introduction to Programming\n'
                    '2. Data Structures\n'
                    '3. Algorithms\n'
                    '4. Object-Oriented Programming\n'
                    '5. Web Development Basics\n\n'
                    '## Learning Outcomes\n'
                    '- Understand fundamental programming concepts\n'
                    '- Implement basic data structures\n'
                    '- Solve problems using algorithms'
                ),
                'students': students,
                'room': 'CS-101',
                'schedule': [
                    {'day': 'monday', 'start': '09:00', 'end': '11:00'},
                     {'day': 'wednesday', 'start': '09:00', 'end': '11:00'}
                    ]
            },
            {
                'code': 'MATH201',
                'name': 'Discrete Mathematics',
                'description': 'Mathematical structures that are fundamentally discrete rather than continuous.',
                'outline': (
                    '## Course Outline\n\n'
                    '1. Logic and Proofs\n'
                    '2. Set Theory\n'
                    '3. Relations and Functions\n'
                    '4. Graph Theory\n\n'
                    '## Learning Outcomes\n'
                    '- Understand mathematical reasoning\n'
                    '- Solve problems using discrete structures\n'
                    '- Apply graph theory concepts'
                ),
                'students': students[:1],  # Only first student
                'room': 'MATH-201',
                'schedule': [
                    {'day': 'tuesday', 'start': '13:00', 'end': '15:00'},
                    {'day': 'thursday', 'start': '13:00', 'end': '15:00'}
                    ]
            },
            {
                'code': 'PHY301',
                'name': 'Physics for Engineers',
                'description': 'Fundamental concepts of physics with engineering applications.',
                'outline': (
                    '## Course Outline\n\n'
                    '1. Mechanics\n'
                    '2. Thermodynamics\n'
                    '3. Electromagnetism\n\n'
                    '## Learning Outcomes\n'
                    '- Apply physics principles to engineering problems\n'
                    '- Understand fundamental physical laws\n'
                    '- Solve practical engineering problems'
                ),
                'students': students,
                'room': 'PHY-301',
                'schedule': [
                    {'day': 'monday', 'start': '14:00', 'end': '16:00'},
                    {'day': 'friday', 'start': '10:00', 'end': '12:00'}
                    ]
            }
        ]
        
        for data in module_data:
            module = Module.objects.create(
                code=data['code'],
                name=data['name'],
                description=data['description'],
                course_outline=data['outline'],
                attendance_threshold=75.0
            )
            module.lecturers.add(lecturer)
            for student in data['students']:
                module.students.add(student)
            
            # Create class schedules
            for session in data['schedule']:
                start_time = time(*map(int, session['start'].split(':')))
                end_time = time(*map(int, session['end'].split(':')))
                
                ClassSchedule.objects.create(
                    module=module,
                    lecturer=lecturer,
                    day_of_week=session['day'],
                    start_time=start_time,
                    end_time=end_time,
                    room=data['room']
                )
            
            modules.append(module)
        
        return modules
    
    def create_attendance_records(self, modules, students):
        """Create sample attendance records"""
        now = timezone.now()
        
        for module in modules:
            # Create past sessions for attendance
            for days_ago in range(1, 15, 2):  # Every other day for 2 weeks
                session_date = now - timedelta(days=days_ago)
                qr = QRCode.objects.create(
                    module=module,
                    lecturer=module.lecturers.first(),
                    session_date=session_date,
                    expiration_minutes=60,
                    is_active=False
                )
                
                # Mark attendance for some students
                for i, student in enumerate(students):
                    if student in module.students.all():
                        # Randomly mark some students as present (75% chance)
                        status = 'present' if random.random() < 0.75 else 'absent'
                        Attendance.objects.create(
                            student=student,
                            qrcode=qr,
                            status=status,
                            timestamp=session_date + timedelta(minutes=5)
                        )
    
    def handle(self, *args, **options):
        User = get_user_model()
        
        # Clear existing data
        self.stdout.write('Clearing existing data...')
        User.objects.filter(is_superuser=False).delete()
        Module.objects.all().delete()
        ClassSchedule.objects.all().delete()
        
        # Create test users
        self.stdout.write('Creating test users...')
        lecturer = User.objects.create_user(
            username='lecturer1',
            email='lecturer1@example.com',
            password='testpass123',
            is_lecturer=True,
            first_name='John',
            last_name='Doe'
        )
        
        students = []
        for i in range(1, 4):
            student = User.objects.create_user(
                username=f'student{i}',
                email=f'student{i}@example.com',
                password='testpass123',
                is_student=True,
                first_name=f'Student{chr(64+i)}',
                last_name='Smith'
            )
            students.append(student)
        
        # Create modules with schedules and attendance
        self.stdout.write('Creating test modules and schedules...')
        modules = self.create_sample_modules(lecturer, students)
        
        # Create attendance records
        self.stdout.write('Creating attendance records...')
        self.create_attendance_records(modules, students)
        
        # Create upcoming QR codes
        self.stdout.write('Creating upcoming sessions...')
        for module in modules:
            for days_ahead in [1, 3, 7]:  # Create sessions for next 1, 3, and 7 days
                session_date = timezone.now() + timedelta(days=days_ahead, hours=9)  # 9 AM
                QRCode.objects.create(
                    module=module,
                    lecturer=module.lecturers.first(),
                    session_date=session_date,
                    expiration_minutes=60,
                    is_active=True
                )
        
        self.stdout.write(self.style.SUCCESS('''
        Successfully loaded test data!
        
        Test accounts:
        - Lecturer: lecturer1 / testpass123
        - Students: student1, student2, student3 / testpass123
        
        Visit /schedule/ to see the class schedule
        '''))
