from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from calendersync.models import GoogleCredentials
from django.utils.timezone import is_naive, make_aware
from meetings.models import Meeting 
import pytz


def create_google_event(user, meeting):
    try:
        creds_obj = GoogleCredentials.objects.get(user=user)
    except GoogleCredentials.DoesNotExist:
        print("❌ No credentials found.")
        return

    creds = Credentials(
        token=creds_obj.token,
        refresh_token=creds_obj.refresh_token,
        token_uri=creds_obj.token_uri,
        client_id=creds_obj.client_id,
        client_secret=creds_obj.client_secret,
        scopes=creds_obj.scopes.split(','),
    )

    # Ensure times are timezone-aware
    if is_naive(meeting.start_time):
        meeting.start_time = make_aware(meeting.start_time, timezone=pytz.timezone('Asia/Karachi'))
    if is_naive(meeting.end_time):
        meeting.end_time = make_aware(meeting.end_time, timezone=pytz.timezone('Asia/Karachi'))

    service = build('calendar', 'v3', credentials=creds)

    event = {
        'summary': meeting.title,
        'description': f'Join meeting: {meeting.join_url}',
        'start': {
            'dateTime': meeting.start_time.isoformat(),
            'timeZone': 'Asia/Karachi',
        },
        'end': {
            'dateTime': meeting.end_time.isoformat(),
            'timeZone': 'Asia/Karachi',
        },
        'attendees': [{'email': u.email} for u in meeting.participants.all()],
        'reminders': {'useDefault': True},
    }

    created_event = service.events().insert(calendarId='primary', body=event).execute()
    print("✅ Created Google Event:", created_event)

    # 🔁 Reload real object from DB and save
    real_meeting = Meeting.objects.get(id=meeting.id)
    real_meeting.google_event_id = created_event['id']
    real_meeting.save()



