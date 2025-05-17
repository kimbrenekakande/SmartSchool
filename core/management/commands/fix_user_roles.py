from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()

class Command(BaseCommand):
    help = 'Check and fix user roles (is_student, is_lecturer)'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username to check/update')
        parser.add_argument('--role', type=str, choices=['student', 'lecturer', 'both'], 
                          help='Role to assign to the user')

    def handle(self, *args, **options):
        username = options['username']
        role = options.get('role')

        try:
            with transaction.atomic():
                user = User.objects.select_for_update().get(username=username)
                self.stdout.write(self.style.SUCCESS(f'Found user: {user.username}'))
                self.stdout.write(f'Current roles - is_student: {user.is_student}, is_lecturer: {user.is_lecturer}, is_superuser: {user.is_superuser}')
                
                if role:
                    if role == 'student':
                        user.is_student = True
                        user.is_lecturer = False
                    elif role == 'lecturer':
                        user.is_student = False
                        user.is_lecturer = True
                    elif role == 'both':
                        user.is_student = True
                        user.is_lecturer = True
                    
                    user.save()
                    self.stdout.write(self.style.SUCCESS(f'Updated roles - is_student: {user.is_student}, is_lecturer: {user.is_lecturer}'))
                
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User {username} does not exist'))
