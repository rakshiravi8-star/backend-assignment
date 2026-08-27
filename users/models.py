import secrets
import string
from datetime import timedelta

from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

OTP_TTL_MINUTES = 10
OTP_RESEND_COOLDOWN_SECONDS = 30
OTP_MAX_FAILED_ATTEMPTS = 5


class Profile(models.Model):
	class Role(models.TextChoices):
		SEEKER = 'SEEKER', 'Seeker'
		FACILITATOR = 'FACILITATOR', 'Facilitator'

	user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
	role = models.CharField(max_length=20, choices=Role.choices)
	is_email_verified = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)


class EmailOTP(models.Model):
	user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='email_otp')
	otp_hash = models.CharField(max_length=128)
	created_at = models.DateTimeField()
	last_sent_at = models.DateTimeField()
	expires_at = models.DateTimeField()
	failed_attempts = models.PositiveSmallIntegerField(default=0)

	def is_expired(self):
		return timezone.now() >= self.expires_at

	def is_locked(self):
		return self.failed_attempts >= OTP_MAX_FAILED_ATTEMPTS

	def set_new_otp(self, raw_otp):
		now = timezone.now()
		self.otp_hash = make_password(raw_otp)
		self.created_at = now
		self.last_sent_at = now
		self.expires_at = now + timedelta(minutes=OTP_TTL_MINUTES)
		self.failed_attempts = 0

	def check_otp(self, raw_otp):
		return check_password(raw_otp, self.otp_hash)

	@staticmethod
	def generate_raw_otp():
		return ''.join(secrets.choice(string.digits) for _ in range(6))

# Create your models here.
