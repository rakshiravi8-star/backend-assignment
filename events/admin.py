from django.contrib import admin

from .models import Enrollment, Event


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
	list_display = ('title', 'created_by', 'starts_at', 'ends_at', 'capacity')
	search_fields = ('title', 'description')


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
	list_display = ('event', 'seeker', 'status', 'created_at')