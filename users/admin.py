from django.contrib import admin

from .models import EmailOTP, Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
	list_display = ('user', 'role', 'is_email_verified', 'created_at')
	list_filter = ('role', 'is_email_verified')
	search_fields = ('user__email',)


@admin.register(EmailOTP)
class EmailOTPAdmin(admin.ModelAdmin):
	list_display = ('user', 'created_at', 'expires_at', 'failed_attempts')
	readonly_fields = ('otp_hash',)
