from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from .models import EmailOTP, Profile
from events.test_event_suite import ConcurrentEnrollmentTests, EventEnrollmentTests


class AuthFlowTests(TestCase):
	def setUp(self):
		self.client = APIClient()

	def test_signup_normalizes_email_and_hashes_otp(self):
		response = self.client.post('/api/auth/signup/', {
			'email': ' Alice@Example.com ', 'password': 'StrongPass123!', 'role': 'SEEKER',
		})
		self.assertEqual(response.status_code, 201)
		user = User.objects.get(email='alice@example.com')
		self.assertFalse(user.profile.is_email_verified)
		self.assertTrue(user.email_otp.otp_hash.startswith('pbkdf2_'))
		self.assertNotIn('otp', response.data)

	def test_wrong_otp_counts_and_lockout(self):
		self.client.post('/api/auth/signup/', {
			'email': 'alice@example.com', 'password': 'StrongPass123!', 'role': 'SEEKER',
		})
		for _ in range(5):
			response = self.client.post('/api/auth/verify-email/', {'email': 'alice@example.com', 'otp': '000000'})
		self.assertEqual(response.data['code'], 'invalid_otp')
		response = self.client.post('/api/auth/verify-email/', {'email': 'alice@example.com', 'otp': '000000'})
		self.assertEqual(response.data['code'], 'otp_locked')

	def test_verify_then_login_returns_jwt(self):
		self.client.post('/api/auth/signup/', {
			'email': 'alice@example.com', 'password': 'StrongPass123!', 'role': 'FACILITATOR',
		})
		user = User.objects.get(email='alice@example.com')
		user.email_otp.set_new_otp('123456')
		user.email_otp.save()
		response = self.client.post('/api/auth/verify-email/', {'email': user.email, 'otp': '123456'})
		self.assertEqual(response.status_code, 200)
		response = self.client.post('/api/auth/login/', {'email': user.email, 'password': 'StrongPass123!'})
		self.assertEqual(response.status_code, 200)
		self.assertIn('access', response.data)
		self.assertEqual(response.data['role'], Profile.Role.FACILITATOR)

	def test_expired_otp_is_rejected(self):
		self.client.post('/api/auth/signup/', {
			'email': 'alice@example.com', 'password': 'StrongPass123!', 'role': 'SEEKER',
		})
		otp = EmailOTP.objects.get(user__email='alice@example.com')
		otp.expires_at = timezone.now() - timedelta(seconds=1)
		otp.save(update_fields=['expires_at'])
		response = self.client.post('/api/auth/verify-email/', {'email': 'alice@example.com', 'otp': '000000'})
		self.assertEqual(response.data['code'], 'otp_expired')

	def test_invalid_role_and_duplicate_verified_email_are_rejected(self):
		response = self.client.post('/api/auth/signup/', {
			'email': 'bad@example.com', 'password': 'StrongPass123!', 'role': 'ADMIN',
		})
		self.assertEqual(response.status_code, 400)
		self.client.post('/api/auth/signup/', {
			'email': 'bad@example.com', 'password': 'StrongPass123!', 'role': 'SEEKER',
		})
		user = User.objects.get(email='bad@example.com')
		user.profile.is_email_verified = True
		user.profile.save(update_fields=['is_email_verified'])
		response = self.client.post('/api/auth/signup/', {
			'email': 'bad@example.com', 'password': 'StrongPass123!', 'role': 'SEEKER',
		})
		self.assertEqual(response.status_code, 409)
		self.assertEqual(response.data['code'], 'email_already_registered')

	def test_resend_replaces_old_otp_and_enforces_cooldown(self):
		with patch('users.models.EmailOTP.generate_raw_otp', return_value='111111'):
			self.client.post('/api/auth/signup/', {
				'email': 'resend@example.com', 'password': 'StrongPass123!', 'role': 'SEEKER',
			})
		user = User.objects.get(email='resend@example.com')
		old_hash = user.email_otp.otp_hash
		response = self.client.post('/api/auth/signup/', {
			'email': 'resend@example.com', 'password': 'StrongPass123!', 'role': 'SEEKER',
		})
		self.assertEqual(response.status_code, 429)
		user.email_otp.last_sent_at = timezone.now() - timedelta(seconds=31)
		user.email_otp.save(update_fields=['last_sent_at'])
		with patch('users.models.EmailOTP.generate_raw_otp', return_value='222222'):
			response = self.client.post('/api/auth/signup/', {
				'email': 'resend@example.com', 'password': 'StrongPass123!', 'role': 'SEEKER',
			})
		self.assertEqual(response.status_code, 200)
		user.email_otp.refresh_from_db()
		self.assertNotEqual(old_hash, user.email_otp.otp_hash)
		self.assertFalse(user.email_otp.check_otp('111111'))
		self.assertTrue(user.email_otp.check_otp('222222'))

	def test_unverified_and_wrong_password_login_fail_and_refresh_succeeds(self):
		self.client.post('/api/auth/signup/', {
			'email': 'login@example.com', 'password': 'StrongPass123!', 'role': 'SEEKER',
		})
		response = self.client.post('/api/auth/login/', {'email': 'login@example.com', 'password': 'StrongPass123!'})
		self.assertEqual(response.status_code, 403)
		user = User.objects.get(email='login@example.com')
		user.profile.is_email_verified = True
		user.profile.save(update_fields=['is_email_verified'])
		response = self.client.post('/api/auth/login/', {'email': user.email, 'password': 'wrong-password'})
		self.assertEqual(response.status_code, 401)
		response = self.client.post('/api/auth/login/', {'email': user.email, 'password': 'StrongPass123!'})
		self.assertEqual(response.status_code, 200)
		refresh = response.data['refresh']
		response = self.client.post('/api/auth/refresh/', {'refresh': refresh})
		self.assertEqual(response.status_code, 200)
		self.assertIn('access', response.data)
