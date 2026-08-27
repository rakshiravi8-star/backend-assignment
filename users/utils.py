import uuid

from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import send_mail


def generate_unique_username():
    for _ in range(5):
        candidate = f'user_{uuid.uuid4().hex[:12]}'
        if not User.objects.filter(username=candidate).exists():
            return candidate
    raise RuntimeError('Could not generate a unique username.')


def send_otp_email(to_email, raw_otp):
    send_mail(
        subject='Your verification code',
        message=f'Your verification code is {raw_otp}. It expires in 10 minutes.',
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@events-platform.local'),
        recipient_list=[to_email],
        fail_silently=False,
    )