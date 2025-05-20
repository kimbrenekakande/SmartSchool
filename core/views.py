from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, update_session_auth_hash
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.contrib import messages
from django.views.generic import TemplateView
from django.conf import settings

class HomeView(TemplateView):
    template_name = 'core/home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'is_home': True,
            'STATIC_URL': '/static/',
            'debug': settings.DEBUG
        })
        return context
        
    def get(self, request, *args, **kwargs):
        # If user is already authenticated, redirect to appropriate dashboard
        if request.user.is_authenticated:
            if hasattr(request.user, 'is_student') and request.user.is_student:
                from django.urls import reverse
                return redirect('dashboard:student_dashboard')
            elif hasattr(request.user, 'is_lecturer') and request.user.is_lecturer:
                return redirect('dashboard:lecturer_dashboard')
            elif request.user.is_superuser:
                return redirect('dashboard:admin_dashboard')
        return super().get(request, *args, **kwargs)

@login_required
def profile(request):
    return render(request, 'core/profile.html', {'is_profile': True})

@login_required
def update_profile(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated successfully.')
            return redirect('core:profile')
    else:
        form = ProfileForm(instance=request.user)
    return render(request, 'core/update_profile.html', {'form': form})

@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password was successfully updated!')
            return redirect('core:profile')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'core/change_password.html', {'form': form})
