from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from common.exceptions import EmailAlreadyRegistered, EmailNotVerified, InvalidCredentials, InvalidOTP, OTPExpired, OTPLocked, ResendCooldownActive
from .models import EmailOTP, OTP_RESEND_COOLDOWN_SECONDS, Profile
from .serializers import LoginSerializer, SignupSerializer, VerifyEmailSerializer
from .utils import generate_unique_username, send_otp_email


class SignupView(APIView):
	permission_classes = [AllowAny]

	def post(self, request):
		serializer = SignupSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		email = serializer.validated_data['email']
		with transaction.atomic():
			user = User.objects.select_for_update().filter(email=email).first()
			created = user is None
			if user:
				if user.profile.is_email_verified:
					raise EmailAlreadyRegistered()
				otp = EmailOTP.objects.select_for_update().get(user=user)
				if (timezone.now() - otp.last_sent_at).total_seconds() < OTP_RESEND_COOLDOWN_SECONDS:
					raise ResendCooldownActive()
				user.set_password(serializer.validated_data['password'])
				user.save(update_fields=['password'])
				user.profile.role = serializer.validated_data['role']
				user.profile.save(update_fields=['role'])
			else:
				try:
					user = User.objects.create_user(username=generate_unique_username(), email=email, password=serializer.validated_data['password'])
				except IntegrityError as exc:
					raise EmailAlreadyRegistered() from exc
				Profile.objects.create(user=user, role=serializer.validated_data['role'])
				otp = EmailOTP(user=user)
			raw_otp = EmailOTP.generate_raw_otp()
			otp.set_new_otp(raw_otp)
			otp.save()
			send_otp_email(email, raw_otp)
		status_code = 201 if created else 200
		return Response({'detail': 'Signup successful. A verification code has been sent to your email.', 'email': email}, status=status_code)


class VerifyEmailView(APIView):
	permission_classes = [AllowAny]

	def post(self, request):
		serializer = VerifyEmailSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		with transaction.atomic():
			user = User.objects.select_for_update().filter(email=serializer.validated_data['email']).first()
			if not user:
				raise InvalidOTP()
			if user.profile.is_email_verified:
				return Response({'detail': 'Email already verified.'})
			otp = EmailOTP.objects.select_for_update().filter(user=user).first()
			if not otp:
				raise InvalidOTP()
			if otp.is_locked():
				raise OTPLocked()
			if otp.is_expired():
				raise OTPExpired()
			if not otp.check_otp(serializer.validated_data['otp']):
				otp.failed_attempts += 1
				otp.save(update_fields=['failed_attempts'])
				return Response({'detail': 'Invalid verification code.', 'code': 'invalid_otp'}, status=400)
			user.profile.is_email_verified = True
			user.profile.save(update_fields=['is_email_verified'])
			otp.delete()
		return Response({'detail': 'Email verified successfully.'})


class LoginView(APIView):
	permission_classes = [AllowAny]

	def post(self, request):
		serializer = LoginSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		user = User.objects.filter(email=serializer.validated_data['email']).first()
		if not user or not user.check_password(serializer.validated_data['password']):
			raise InvalidCredentials()
		profile = getattr(user, 'profile', None)
		if not profile or not profile.is_email_verified:
			raise EmailNotVerified()
		if not user.is_active:
			raise InvalidCredentials()
		refresh = RefreshToken.for_user(user)
		return Response({'access': str(refresh.access_token), 'refresh': str(refresh), 'role': profile.role})
