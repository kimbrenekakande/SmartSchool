import os
import sys

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_auth.settings')
import django
django.setup()

def clean_database():
    """Clean the database by removing all data and creating a superuser."""
    from django.contrib.auth import get_user_model
    from django.db import connection
    
    # Get all models from all installed apps
    from django.apps import apps
    
    # Don't delete these models
    EXCLUDED_MODELS = ['contenttypes.ContentType', 'auth.Permission', 'sessions.Session', 'admin.LogEntry']
    
    # Delete data from all models
    for model in apps.get_models():
        model_name = f"{model._meta.app_label}.{model._meta.model_name}"
        if model_name not in EXCLUDED_MODELS:
            try:
                model.objects.all().delete()
                print(f"Deleted all objects from {model_name}")
            except Exception as e:
                print(f"Error deleting from {model_name}: {e}")
    
    # Reset SQLite sequences
    with connection.cursor() as cursor:
        # SQLite specific: reset auto-increment counters
        cursor.execute("DELETE FROM sqlite_sequence;")
    
    # Create a superuser
    User = get_user_model()
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@example.com', 'admin')
        print("Created superuser: admin / admin")
    
    print("\nDatabase has been cleaned successfully!")

if __name__ == "__main__":
    print("Cleaning database and creating a new superuser...")
    clean_database()
    print("\nYou can now log in with:")
    print("Username: admin")
    print("Password: admin")
