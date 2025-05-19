"""
URL configuration for school_auth project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

def root_redirect(request):
    if request.user.is_authenticated:
        if request.user.is_student:
            return redirect('dashboard:student_dashboard')
        elif request.user.is_lecturer:
            return redirect('dashboard:lecturer_dashboard')
        elif request.user.is_superuser:
            return redirect('dashboard:admin_dashboard')
    return redirect('attendance:login')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('dashboard/', include('dashboard.urls')),
    path('attendance/', include('attendance.urls')),
    path('core/', include('core.urls')),
    path('', root_redirect, name='root_redirect'),
    path('accounts/login/', RedirectView.as_view(url='/attendance/login/')),  # For admin redirects
    path('accounts/profile/', RedirectView.as_view(url='/')),  # For admin redirects
]

# Serve static and media files in development
if settings.DEBUG:
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    
    # Serve static files
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
    # Serve media files
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
    # Debug toolbar
    try:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns
    except ImportError:
        pass
