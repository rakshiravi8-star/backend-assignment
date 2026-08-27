from django.urls import path

from .views import CancelEnrollmentView, EnrollView, EventDiscoveryListView, FacilitatorEventDetailView, FacilitatorEventListCreateView, MyEnrollmentListView

urlpatterns = [
    path('facilitator/events/', FacilitatorEventListCreateView.as_view()),
    path('facilitator/events/<uuid:pk>/', FacilitatorEventDetailView.as_view()),
    path('events/', EventDiscoveryListView.as_view()),
    path('events/<uuid:event_id>/enroll/', EnrollView.as_view()),
    path('events/<uuid:event_id>/cancel/', CancelEnrollmentView.as_view()),
    path('enrollments/', MyEnrollmentListView.as_view()),
]