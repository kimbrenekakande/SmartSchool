import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_auth.settings')
django.setup()

from django.contrib.auth.models import User

try:
    User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='admin123'
    )
    print("Superuser created successfully!")
except:
    print("Superuser already exists or creation failed.")
