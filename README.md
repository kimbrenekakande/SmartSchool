# Smart School Attendance System

A comprehensive school attendance system built with Django and Tailwind CSS.

## Features

- Role-based dashboards for Admin, Lecturers, and Students
- QR-based attendance system
- Server-side attendance analytics
- Modern UI with Tailwind CSS
- Session-based security

## Setup Instructions

1. Create and activate virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run migrations:
```bash
python3 manage.py migrate
```

4. Create superuser:
```bash
python3 manage.py createsuperuser
```

5. Start the development server:
```bash
python3 manage.py runserver
```

## Project Structure

```
school_auth/
├── attendance/     # Attendance management app
├── dashboard/      # Role-specific dashboards
├── core/           # Core authentication and middleware
├── static/         # Static files (Tailwind CSS)
└── templates/      # Django templates
```
