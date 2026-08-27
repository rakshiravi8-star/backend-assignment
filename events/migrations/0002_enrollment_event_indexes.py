from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('events', '0001_initial')]

    operations = [
        migrations.AddIndex(
            model_name='event',
            index=models.Index(fields=['starts_at'], name='events_event_starts_idx'),
        ),
        migrations.AddIndex(
            model_name='event',
            index=models.Index(fields=['location'], name='events_event_location_idx'),
        ),
        migrations.AddIndex(
            model_name='event',
            index=models.Index(fields=['language'], name='events_event_language_idx'),
        ),
        migrations.AddIndex(
            model_name='event',
            index=models.Index(fields=['created_by'], name='events_event_created_by_idx'),
        ),
        migrations.AddIndex(
            model_name='enrollment',
            index=models.Index(fields=['event', 'status'], name='events_enroll_event_status_idx'),
        ),
        migrations.AddIndex(
            model_name='enrollment',
            index=models.Index(fields=['seeker', 'status'], name='events_enroll_seek_status_idx'),
        ),
    ]