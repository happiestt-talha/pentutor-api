from celery import shared_task
from .models import FailedSync, GoogleCredentials, CalendarEvent
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from .views import start_watch
import requests
import logging


logger = logging.getLogger(__name__)

@shared_task
def retry_failed_syncs():
    failed_jobs = FailedSync.objects.filter(status='pending')

    for job in failed_jobs:
        try:
            creds_obj = GoogleCredentials.objects.get(user=job.user)

            creds = Credentials(
                token=creds_obj.token,
                refresh_token=creds_obj.refresh_token,
                token_uri=creds_obj.token_uri,
                client_id=creds_obj.client_id,
                client_secret=creds_obj.client_secret,
                scopes=creds_obj.scopes.split(','),
            )

            if creds.expired and creds.refresh_token:
                creds.refresh(Request())

            service = build('calendar', 'v3', credentials=creds)

            events = service.events().list(
                calendarId='primary',
                maxResults=5,
                orderBy='startTime',
                singleEvents=True
            ).execute().get('items', [])

            for event in events:
                event_id = event['id']
                summary = event.get('summary', 'No Title')
                start = event['start'].get('dateTime') or event['start'].get('date')
                end = event['end'].get('dateTime') or event['end'].get('date')
                updated = event['updated']

                CalendarEvent.objects.update_or_create(
                    event_id=event_id,
                    user=creds_obj.user,
                    defaults={
                        'summary': summary,
                        'start_time': parse_datetime(start),
                        'end_time': parse_datetime(end),
                        'updated': parse_datetime(updated),
                    }
                )

            job.status = 'success'
            job.retry_count += 1
            job.save()

        except Exception as e:
            job.retry_count += 1
            job.reason = str(e)
            if job.retry_count >= 3:
                job.status = 'failed'
            job.save()
            logger.error(f"Retry failed for user {job.user}: {e}")


@shared_task
def auto_renew_calendar_watches():
    now = timezone.now()
    buffer_time = now + timezone.timedelta(days=1)  # renew 1 day before expiration

    creds_list = GoogleCredentials.objects.filter(expiration__lte=buffer_time)

    for creds in creds_list:
        try:
            start_watch(creds.user)
            print(f"Renewed watch for user {creds.user}")
        except Exception as e:
            print(f"Failed to renew watch for {creds.user}: {e}")


@shared_task
def cleanup_expired_calendar_channels():
    now = timezone.now()
    expired_creds = GoogleCredentials.objects.filter(expiry__lt=now)

    for creds in expired_creds:
        try:
            if creds.channel_id and creds.resource_id:
                stop_url = 'https://www.googleapis.com/calendar/v3/channels/stop'
                headers = {
                    'Authorization': f'Bearer {creds.token}',
                    'Content-Type': 'application/json'
                }
                data = {
                    'id': creds.channel_id,
                    'resourceId': creds.resource_id
                }

                requests.post(stop_url, headers=headers, json=data)

            creds.delete()
            print(f"[Cleanup] Deleted expired credentials for user {creds.user}")
        except Exception as e:
            print(f"[Cleanup] Failed to delete creds for {creds.user}: {e}")




