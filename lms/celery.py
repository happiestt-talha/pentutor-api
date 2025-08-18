import os
from celery import Celery
from celery.schedules import crontab 

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lms.settings')

app = Celery('authentication')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'auto-renew-calendar-watch-daily': {
        'task': 'calendersync.tasks.auto_renew_calendar_watches',
        'schedule': crontab(hour=0, minute=0),  # runs daily at midnight
    },
    'cleanup-expired-calendar-watches-daily': {
        'task': 'calendersync.tasks.cleanup_expired_calendar_channels',
        'schedule': crontab(hour=1, minute=0),  # every day at 1 AM
    },
    # Email automation tasks
    'generate-weekly-progress-reports': {
        'task': 'email_automation.tasks.generate_weekly_progress_reports',
        'schedule': crontab(hour=9, minute=0, day_of_week=1),  # Every Monday at 9 AM
    },
    'process-email-queue': {
        'task': 'email_automation.tasks.process_email_queue',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
    },
    'cleanup-old-email-logs': {
        'task': 'email_automation.tasks.cleanup_old_email_logs',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
    },
}