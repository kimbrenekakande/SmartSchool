from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def test_view(request):
    return render(request, 'attendance/test_template.html', {
        'total_qrcodes': 10,
        'active_qrcodes': 5,
        'expired_qrcodes': 5
    })
