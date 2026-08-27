from django.db import transaction
from django.db.models import Case, Count, IntegerField, Q, Value, When
from django.utils import timezone
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.exceptions import EventFull
from common.pagination import DefaultPagination
from .models import Enrollment, Event
from .permissions import IsFacilitator, IsSeeker
from .serializers import EnrollmentSerializer, EventSerializer, FacilitatorEventListSerializer


class FacilitatorEventListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, IsFacilitator]
    pagination_class = DefaultPagination

    def get_serializer_class(self):
        return FacilitatorEventListSerializer if self.request.method == 'GET' else EventSerializer

    def get_queryset(self):
        return Event.objects.filter(created_by=self.request.user).annotate(
            enrollment_count=Count('enrollments', filter=Q(enrollments__status=Enrollment.Status.ENROLLED))
        ).order_by('starts_at')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class FacilitatorEventDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, IsFacilitator]
    serializer_class = EventSerializer

    def get_queryset(self):
        return Event.objects.filter(created_by=self.request.user)


class EventDiscoveryListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = EventSerializer
    pagination_class = DefaultPagination

    def get_queryset(self):
        params = self.request.query_params
        query = Event.objects.all()
        if params.get('q'):
            query = query.filter(Q(title__icontains=params['q']) | Q(description__icontains=params['q']))
        for field in ('location', 'language'):
            if params.get(field):
                query = query.filter(**{f'{field}__icontains': params[field]})
        if params.get('starts_after'):
            query = query.filter(starts_at__gte=params['starts_after'])
        if params.get('starts_before'):
            query = query.filter(starts_at__lte=params['starts_before'])
        now = timezone.now()
        return query.annotate(
            upcoming_rank=Case(
                When(starts_at__gte=now, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            )
        ).order_by('upcoming_rank', 'starts_at')


class EnrollView(APIView):
    permission_classes = [IsAuthenticated, IsSeeker]

    def post(self, request, event_id):
        with transaction.atomic():
            try:
                event = Event.objects.select_for_update().get(id=event_id)
            except Event.DoesNotExist:
                return Response({'detail': 'Event not found.', 'code': 'not_found'}, status=404)
            enrollment, created = Enrollment.objects.select_for_update().get_or_create(event=event, seeker=request.user)
            if not created and enrollment.status == Enrollment.Status.ENROLLED:
                return Response(EnrollmentSerializer(enrollment).data)
            if event.capacity is not None and Enrollment.objects.filter(event=event, status=Enrollment.Status.ENROLLED).exclude(pk=enrollment.pk).count() >= event.capacity:
                raise EventFull()
            enrollment.status = Enrollment.Status.ENROLLED
            enrollment.save()
        return Response(EnrollmentSerializer(enrollment).data, status=201 if created else 200)


class CancelEnrollmentView(APIView):
    permission_classes = [IsAuthenticated, IsSeeker]

    def post(self, request, event_id):
        with transaction.atomic():
            enrollment = Enrollment.objects.select_for_update().filter(
                event_id=event_id, seeker=request.user,
            ).first()
            if enrollment is None:
                return Response({'detail': 'Enrollment not found.', 'code': 'not_found'}, status=404)
            enrollment.status = Enrollment.Status.CANCELED
            enrollment.save(update_fields=['status', 'updated_at'])
        return Response(EnrollmentSerializer(enrollment).data)


class MyEnrollmentListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsSeeker]
    serializer_class = EnrollmentSerializer
    pagination_class = DefaultPagination

    def get_queryset(self):
        now = timezone.now()
        query = Enrollment.objects.filter(seeker=self.request.user).select_related('event')
        lookup = 'lt' if self.request.query_params.get('scope') == 'past' else 'gte'
        return query.filter(**{f'event__starts_at__{lookup}': now}).order_by('event__starts_at')