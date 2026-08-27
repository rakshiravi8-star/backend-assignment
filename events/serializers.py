from rest_framework import serializers

from .models import Enrollment, Event


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ['id', 'title', 'description', 'language', 'location', 'starts_at', 'ends_at', 'capacity', 'created_by', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']

    def validate(self, attrs):
        starts_at = attrs.get('starts_at', getattr(self.instance, 'starts_at', None))
        ends_at = attrs.get('ends_at', getattr(self.instance, 'ends_at', None))
        if starts_at and ends_at and starts_at >= ends_at:
            raise serializers.ValidationError('starts_at must be before ends_at.')
        if attrs.get('capacity') is not None and attrs['capacity'] <= 0:
            raise serializers.ValidationError('capacity must be positive when provided.')
        return attrs


class FacilitatorEventListSerializer(EventSerializer):
    enrollment_count = serializers.IntegerField(read_only=True)
    available_seats = serializers.SerializerMethodField()

    class Meta(EventSerializer.Meta):
        fields = EventSerializer.Meta.fields + ['enrollment_count', 'available_seats']

    def get_available_seats(self, obj):
        return None if obj.capacity is None else max(obj.capacity - obj.enrollment_count, 0)


class EnrollmentSerializer(serializers.ModelSerializer):
    event_title = serializers.CharField(source='event.title', read_only=True)

    class Meta:
        model = Enrollment
        fields = ['id', 'event', 'event_title', 'seeker', 'status', 'created_at', 'updated_at']
        read_only_fields = ['id', 'seeker', 'status', 'created_at', 'updated_at']