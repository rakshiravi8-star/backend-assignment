import re

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Profile

OTP_PATTERN = re.compile(r'^\d{6}$')


class SignupSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=Profile.Role.choices)

    def validate_email(self, value):
        return value.strip().lower()

    def validate_password(self, value):
        validate_password(value)
        return value


class VerifyEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField()

    def validate_email(self, value):
        return value.strip().lower()

    def validate_otp(self, value):
        if not OTP_PATTERN.match(value):
            raise serializers.ValidationError('OTP must be a 6-digit code.')
        return value


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate_email(self, value):
        return value.strip().lower()