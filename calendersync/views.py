from django.shortcuts import redirect, HttpResponse
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from django.http import JsonResponse
import datetime
import logging 
import uuid
import requests

from django.conf import settings
from .models import GoogleCredentials, CalendarEvent

from django.contrib.auth import get_user_model
User = get_user_model()

logger = logging.getLogger(__name__)

# user = User.objects.first()

import os

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

GOOGLE_CLIENT_SECRET_FILE = os.path.join(settings.BASE_DIR, 'calendersync', 'client_secret.json')


SCOPES = ['https://www.googleapis.com/auth/calendar']


REDIRECT_URI = "http://localhost:8000/calendar/oauth2callback/"
ADDRESS = "https://448f-43-242-177-73.ngrok-free.app/calendar/notifications/"
REVOKE_URL = 'https://oauth2.googleapis.com/revoke'
STOP_URL = 'https://www.googleapis.com/calendar/v3/channels/stop'

# Views below



def google_calender_auth(request):
    flow = Flow.from_client_secrets_file(
        GOOGLE_CLIENT_SECRET_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )

    auth_url,_=flow.authorization_url(prompt="consent")

    return redirect(auth_url)

@login_required
def oauth2_callback(request):
    # Use the stored state
    state = request.session.get('state')

    flow = Flow.from_client_secrets_file(
        GOOGLE_CLIENT_SECRET_FILE,
        scopes=SCOPES,
        state=state,
        redirect_uri=REDIRECT_URI
    )
    flow.fetch_token(authorization_response=request.build_absolute_uri())

    credentials = flow.credentials

    # Save to database instead of session
    GoogleCredentials.objects.update_or_create(
        user=request.user,  # for deployment
        defaults={
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': ','.join(credentials.scopes),
            'expiry': credentials.expiry,
        }
    )
    start_watch(user)
    
    return redirect('calendar_events')

@csrf_exempt
@login_required
def disconnect_google(request):
    try:
        creds = GoogleCredentials.objects.get(user=request.user)

        # Revoke token via Google
        revoke_url = REVOKE_URL
        params = {'token': creds.token}
        requests.post(revoke_url, params=params)

        if creds.channel_id and creds.resource_id:
            stop_url = STOP_URL
            headers = {'Content-Type': 'application/json'}
            data = {
                'id': creds.channel_id,
                'resourceId': creds.resource_id
            }
            access_token = creds.token
            requests.post(stop_url, headers={
                **headers,
                'Authorization': f'Bearer {access_token}'
            }, json=data)

        # Delete from DB
        creds.delete()

        return JsonResponse({'success': True, 'message': 'Google account disconnected.'})

    except GoogleCredentials.DoesNotExist:
        return JsonResponse({'error': 'No credentials found.'}, status=404)

def calendar_events(request):
    creds_obj = GoogleCredentials.objects.get(user=request.user)

    creds = Credentials(
        token=creds_obj.token,
        refresh_token=creds_obj.refresh_token,
        token_uri=creds_obj.token_uri,
        client_id=creds_obj.client_id,
        client_secret=creds_obj.client_secret,
        scopes=creds_obj.scopes.split(','),
    )

    # ✅ Auto refresh
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())

        # Save refreshed token
        creds_obj.token = creds.token
        creds_obj.expiry = creds.expiry.isoformat() if creds.expiry else None
        creds_obj.save()

    service = build('calendar', 'v3', credentials=creds)

    event = {
        'summary': 'Synced Event',
        'start': {'dateTime': '2025-07-01T10:00:00+05:00'},
        'end': {'dateTime': '2025-07-01T11:00:00+05:00'},
    }

    service.events().insert(calendarId='primary', body=event).execute()
    return HttpResponse("Event created with refreshed token!")

@csrf_exempt
def calendar_notification(request):
    if request.method == 'POST':
        channel_id = request.headers.get('X-Goog-Channel-ID')
        resource_id = request.headers.get('X-Goog-Resource-ID')
        resource_state = request.headers.get('X-Goog-Resource-State')

        logger.info(f"Webhook received: {channel_id} | {resource_state} | {resource_id}")

        try:
            creds_obj = GoogleCredentials.objects.get(channel_id=channel_id)

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

            events_result = service.events().list(
                calendarId='primary',
                maxResults=5,
                orderBy='startTime',
                singleEvents=True
            ).execute()

            events = events_result.get('items', [])

            for event in events:
                event_id = event['id']
                summary = event.get('summary', 'No Title')
                start = event['start'].get('dateTime') or event['start'].get('date')
                end = event['end'].get('dateTime') or event['end'].get('date')
                updated = event['updated']

                start_dt = parse_datetime(start)
                end_dt = parse_datetime(end)
                updated_dt = parse_datetime(updated)

                CalendarEvent.objects.update_or_create(
                    event_id=event_id,
                    user=creds_obj.user,
                    defaults={
                        'summary': summary,
                        'start_time': start_dt,
                        'end_time': end_dt,
                        'updated': updated_dt,
                    }
                )

            return HttpResponse(status=200)

        except Exception as e:
            # Retry queue entry
            FailedSync.objects.create(
                user=creds_obj.user if 'creds_obj' in locals() else None,
                reason=str(e),
            )
            logger.error(f"Calendar sync failed for channel {channel_id}: {e}")
            return HttpResponse(status=500)

    return HttpResponse("Webhook endpoint ready", status=200)

# It will send a watch request to Google
def start_watch(user):
    creds_obj = GoogleCredentials.objects.get(user=request.user)
    creds = Credentials(
        token=creds_obj.token,
        refresh_token=creds_obj.refresh_token,
        token_uri=creds_obj.token_uri,
        client_id=creds_obj.client_id,
        client_secret=creds_obj.client_secret,
        scopes=creds_obj.scopes.split(','),
    )

    service = build('calendar', 'v3', credentials=creds)

    request_body = {
        'id': str(uuid.uuid4()),  # unique channel ID
        'type': 'web_hook',
        'address': ADDRESS,  # your public webhook URL
    }

    response = service.events().watch(calendarId='primary', body=request_body).execute()

    expiration_timestamp = int(response.get('expiration')) / 1000  
    expiration_time = timezone.datetime.fromtimestamp(expiration_timestamp, tz=timezone.utc)

    creds_obj.channel_id = response.get('id')
    creds_obj.resource_id = response.get('resourceId')
    creds_obj.expiration = expiration_time
    creds_obj.save()
    print("Watch response:", response)

    # ✅ Save the channel ID + resource ID returned by Google
    creds_obj.channel_id = response['id']
    creds_obj.resource_id = response['resourceId']
    creds_obj.save()






# Utility Function
def credentials_to_dict(credentials):
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }