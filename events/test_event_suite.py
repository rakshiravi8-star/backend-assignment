from datetime import timedelta
import threading
from urllib.parse import urlencode

from django.contrib.auth.models import User
from django.db import connection
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import Profile
from events.models import Enrollment, Event


class EventEnrollmentTests(TestCase):
    def setUp(self):
        self.facilitator = User.objects.create_user(username='fac', email='fac@example.com', password='pass12345')
        Profile.objects.create(user=self.facilitator, role=Profile.Role.FACILITATOR, is_email_verified=True)
        self.seeker = User.objects.create_user(username='seek', email='seek@example.com', password='pass12345')
        Profile.objects.create(user=self.seeker, role=Profile.Role.SEEKER, is_email_verified=True)
        self.event = Event.objects.create(
            title='Workshop', language='en', location='Remote', starts_at=timezone.now() + timedelta(days=1),
            ends_at=timezone.now() + timedelta(days=1, hours=1), capacity=1, created_by=self.facilitator,
        )

    def client_for(self, user):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {RefreshToken.for_user(user).access_token}')
        return client

    def test_facilitator_creates_and_seeker_cannot_create(self):
        payload = {
            'title': 'New', 'language': 'en', 'location': 'Remote',
            'starts_at': (timezone.now() + timedelta(days=2)).isoformat(),
            'ends_at': (timezone.now() + timedelta(days=2, hours=1)).isoformat(),
        }
        self.assertEqual(self.client_for(self.facilitator).post('/api/facilitator/events/', payload).status_code, 201)
        self.assertEqual(self.client_for(self.seeker).post('/api/facilitator/events/', payload).status_code, 403)

    def test_own_event_listing_counts_and_protected_access(self):
        self.assertEqual(APIClient().get('/api/events/').status_code, 401)
        Enrollment.objects.create(event=self.event, seeker=self.seeker, status=Enrollment.Status.ENROLLED)
        response = self.client_for(self.facilitator).get('/api/facilitator/events/')
        self.assertEqual(response.status_code, 200)
        result = response.data['results'][0]
        self.assertEqual(result['enrollment_count'], 1)
        self.assertEqual(result['available_seats'], 0)

    def test_enroll_cancel_and_reenroll_reuses_row(self):
        client = self.client_for(self.seeker)
        self.assertEqual(client.post(f'/api/events/{self.event.id}/enroll/').status_code, 201)
        self.assertEqual(client.post(f'/api/events/{self.event.id}/cancel/').status_code, 200)
        self.assertEqual(client.post(f'/api/events/{self.event.id}/enroll/').status_code, 200)
        self.assertEqual(Enrollment.objects.filter(event=self.event, seeker=self.seeker).count(), 1)

    def test_capacity_rejects_second_seeker(self):
        client = self.client_for(self.seeker)
        self.assertEqual(client.post(f'/api/events/{self.event.id}/enroll/').status_code, 201)
        another = User.objects.create_user(username='seek2', email='seek2@example.com', password='pass12345')
        Profile.objects.create(user=another, role=Profile.Role.SEEKER, is_email_verified=True)
        response = self.client_for(another).post(f'/api/events/{self.event.id}/enroll/')
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data['code'], 'event_full')

    def test_facilitator_cannot_enroll_and_seeker_cannot_cancel_another(self):
        response = self.client_for(self.facilitator).post(f'/api/events/{self.event.id}/enroll/')
        self.assertEqual(response.status_code, 403)
        other = User.objects.create_user(username='seek2', email='seek2@example.com', password='pass12345')
        Profile.objects.create(user=other, role=Profile.Role.SEEKER, is_email_verified=True)
        Enrollment.objects.create(event=self.event, seeker=self.seeker, status=Enrollment.Status.ENROLLED)
        response = self.client_for(other).post(f'/api/events/{self.event.id}/cancel/')
        self.assertEqual(response.status_code, 404)

    def test_facilitator_crud_and_other_owner_is_hidden(self):
        client = self.client_for(self.facilitator)
        detail = client.get(f'/api/facilitator/events/{self.event.id}/')
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(client.put(f'/api/facilitator/events/{self.event.id}/', {
            'title': 'Updated', 'description': '', 'language': 'en', 'location': 'Remote',
            'starts_at': (timezone.now() + timedelta(days=2)).isoformat(),
            'ends_at': (timezone.now() + timedelta(days=2, hours=1)).isoformat(), 'capacity': 3,
        }, format='json').status_code, 200)
        self.assertEqual(client.patch(f'/api/facilitator/events/{self.event.id}/', {'title': 'Patched'}, format='json').status_code, 200)
        other = User.objects.create_user(username='fac2', email='fac2@example.com', password='pass12345')
        Profile.objects.create(user=other, role=Profile.Role.FACILITATOR, is_email_verified=True)
        self.assertEqual(self.client_for(other).patch(f'/api/facilitator/events/{self.event.id}/', {'title': 'Nope'}, format='json').status_code, 404)
        self.assertEqual(client.delete(f'/api/facilitator/events/{self.event.id}/').status_code, 204)

    def test_discovery_filters_pagination_and_enrollment_scopes(self):
        past = Event.objects.create(title='Past Search', description='history', language='French', location='Paris',
            starts_at=timezone.now() - timedelta(days=2), ends_at=timezone.now() - timedelta(days=2, hours=-1), created_by=self.facilitator)
        future = Event.objects.create(title='Future Search', description='Django meetup', language='English', location='Chennai',
            starts_at=timezone.now() + timedelta(days=3), ends_at=timezone.now() + timedelta(days=3, hours=1), created_by=self.facilitator)
        client = self.client_for(self.seeker)
        self.assertEqual(client.get('/api/events/?q=meetup').data['results'][0]['id'], str(future.id))
        self.assertEqual(client.get('/api/events/?location=Paris').data['results'][0]['id'], str(past.id))
        self.assertEqual(client.get('/api/events/?language=English').data['results'][0]['id'], str(future.id))
        starts_after = urlencode({'starts_after': (timezone.now() - timedelta(hours=1)).isoformat()})
        starts_before = urlencode({'starts_before': (timezone.now() + timedelta(hours=1)).isoformat()})
        self.assertEqual(client.get(f'/api/events/?{starts_after}').data['count'], 2)
        self.assertEqual(client.get(f'/api/events/?{starts_before}').data['count'], 1)
        self.assertEqual(client.get('/api/events/?q=django&location=Chennai&language=English').data['count'], 1)
        page = client.get('/api/events/?page_size=1').data
        self.assertEqual(set(page), {'count', 'next', 'previous', 'results'})
        Enrollment.objects.create(event=past, seeker=self.seeker, status=Enrollment.Status.ENROLLED)
        Enrollment.objects.create(event=future, seeker=self.seeker, status=Enrollment.Status.CANCELED)
        self.assertEqual(client.get('/api/enrollments/?scope=past').data['count'], 1)
        self.assertEqual(client.get('/api/enrollments/?scope=upcoming').data['count'], 1)


class ConcurrentEnrollmentTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        facilitator = User.objects.create_user(username='fac', email='fac@example.com', password='pass12345')
        Profile.objects.create(user=facilitator, role=Profile.Role.FACILITATOR, is_email_verified=True)
        self.event = Event.objects.create(
            title='Concurrent', language='en', location='Remote', capacity=10,
            starts_at=timezone.now() + timedelta(days=1), ends_at=timezone.now() + timedelta(days=1, hours=1),
            created_by=facilitator,
        )
        self.seekers = []
        for index in range(5):
            user = User.objects.create_user(username=f'seek{index}', email=f'seek{index}@example.com', password='pass12345')
            Profile.objects.create(user=user, role=Profile.Role.SEEKER, is_email_verified=True)
            self.seekers.append(user)
        for index in range(9):
            user = User.objects.create_user(username=f'filler{index}', email=f'filler{index}@example.com', password='pass12345')
            Profile.objects.create(user=user, role=Profile.Role.SEEKER, is_email_verified=True)
            Enrollment.objects.create(event=self.event, seeker=user, status=Enrollment.Status.ENROLLED)

    def enroll(self, user, results, index):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {RefreshToken.for_user(user).access_token}')
        results[index] = client.post(f'/api/events/{self.event.id}/enroll/').status_code
        connection.close()

    def test_capacity_is_not_exceeded_concurrently(self):
        results = [None] * 5
        threads = [threading.Thread(target=self.enroll, args=(user, results, index)) for index, user in enumerate(self.seekers)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(sum(status in (200, 201) for status in results), 1)
        self.assertEqual(results.count(409), 4)
        self.assertEqual(Enrollment.objects.filter(event=self.event, status=Enrollment.Status.ENROLLED).count(), 10)