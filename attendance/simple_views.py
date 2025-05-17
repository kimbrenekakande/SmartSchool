from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def simple_test(request):
    return render(request, 'attendance/simple_test.html', {
        'total_qrcodes': 5,
        'active_qrcodes': 3,
        'expired_qrcodes': 2
    })
