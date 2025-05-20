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

from core.views import HomeView

# Root redirect is now handled by HomeView's get method

urlpatterns = [
    path('admin/', admin.site.urls),
    path('dashboard/', include('dashboard.urls', namespace='dashboard')),
    path('attendance/', include('attendance.urls', namespace='attendance')),
    path('core/', include('core.urls', namespace='core')),
    path('', HomeView.as_view(), name='home'),
    path('accounts/login/', RedirectView.as_view(url='/attendance/login/'), name='login_redirect'),
    path('accounts/profile/', RedirectView.as_view(url='/'), name='profile_redirect'),
    path('favicon.ico', RedirectView.as_view(url=settings.STATIC_URL + 'img/favicon.ico')),
]

# Add URL for favicon.ico to prevent 404 errors
urlpatterns += [
    path('favicon.ico', RedirectView.as_view(url=settings.STATIC_URL + 'img/favicon.ico')),
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
