# Email Automation System for LMS

This document provides comprehensive information about the automated email system implemented for your Django LMS project.

## Features

The email automation system provides the following automated email scenarios:

1. **Course Enrollment Email** - Sent when a student joins a course
2. **Post-Demo Class Email** - Sent after a student attends a demo class
3. **Post-Payment Confirmation Email** - Sent when payment is completed successfully
4. **Weekly Progress Email** - Sent every Monday with student progress summary
5. **New Content Notification** - Sent when new videos/lessons are added to courses

## Architecture

### Components

1. **Models** (`email_automation/models.py`)
   - `EmailTemplate` - Stores email templates for different scenarios
   - `EmailLog` - Tracks all sent emails for monitoring and debugging
   - `EmailPreference` - Manages user email preferences and unsubscribe options
   - `WeeklyProgressReport` - Stores weekly progress data for students
   - `EmailQueue` - Queue system for scheduled emails

2. **Services** (`email_automation/services.py`)
   - `EmailService` - Core service for sending emails
   - `EmailTemplateService` - Manages email templates

3. **Tasks** (`email_automation/tasks.py`)
   - Celery tasks for asynchronous email processing
   - Scheduled tasks for weekly reports and cleanup

4. **Signals** (`email_automation/signals.py`)
   - Django signals to automatically trigger emails on events

## Installation & Setup

### 1. Install Dependencies

The system uses the existing dependencies in your `requirements.txt`. Make sure you have:
- `celery==5.5.2`
- `django-celery-beat==2.8.1`
- `redis==6.1.0`

### 2. Add to Django Settings

The email automation app is already added to `INSTALLED_APPS` in `settings.py`.

### 3. Run Migrations

```bash
source venv/bin/activate
python manage.py makemigrations email_automation
python manage.py migrate
```

### 4. Initialize Email Templates

```bash
python manage.py setup_email_automation --create-preferences
```

### 5. Start Celery Services

You need to run Celery worker and beat scheduler:

```bash
# Terminal 1 - Start Celery Worker
source venv/bin/activate
celery -A lms worker -l info

# Terminal 2 - Start Celery Beat Scheduler
source venv/bin/activate
celery -A lms beat -l info
```

### 6. Install and Start Redis (if not already running)

```bash
# On Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis-server

# On macOS
brew install redis
brew services start redis

# On Windows (using WSL or Docker)
docker run -d -p 6379:6379 redis:alpine
```

## Email Configuration

### Development Mode (Default)

Currently configured to print emails to console:
```python
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
```

### Production Mode

Update `settings.py` for production email sending:

#### SMTP Configuration (Gmail example)
```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'  # Use App Password for Gmail
DEFAULT_FROM_EMAIL = 'your-email@gmail.com'
```

#### SendGrid Configuration
```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.sendgrid.net'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'apikey'
EMAIL_HOST_PASSWORD = 'your-sendgrid-api-key'
DEFAULT_FROM_EMAIL = 'noreply@yourdomain.com'
```

#### Mailgun Configuration
```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.mailgun.org'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'postmaster@your-mailgun-domain.com'
EMAIL_HOST_PASSWORD = 'your-mailgun-password'
DEFAULT_FROM_EMAIL = 'noreply@yourdomain.com'
```

## Usage

### Automatic Email Triggers

The system automatically sends emails based on these events:

1. **Student Enrollment** - Triggered by `Enrollment` model creation
2. **Payment Success** - Triggered by `Payment` model update to `is_successful=True`
3. **Demo Class Completion** - Triggered when participant leaves a demo meeting
4. **New Content** - Triggered when new `Video` is created
5. **Weekly Progress** - Scheduled every Monday at 9 AM

### Manual Email Sending

You can also send emails programmatically:

```python
from email_automation.services import EmailService
from django.contrib.auth import get_user_model
from courses.models import Course

User = get_user_model()
email_service = EmailService()

# Send enrollment email
user = User.objects.get(email='student@example.com')
course = Course.objects.get(id=1)

success = email_service.send_email(
    recipient=user,
    email_type='enrollment',
    course=course,
    context={'custom_message': 'Welcome to our special course!'}
)
```

### Bulk Email Sending

```python
from email_automation.services import EmailService

email_service = EmailService()
users = User.objects.filter(role='student')

results = email_service.send_bulk_email(
    recipients=users,
    email_type='new_content',
    context={'new_content_description': 'New Python tutorial series added!'}
)

print(f"Sent: {results['success']}, Failed: {results['failed']}")
```

### Scheduled Email Queue

```python
from email_automation.services import EmailService
from django.utils import timezone
from datetime import timedelta

email_service = EmailService()

# Schedule email for later
scheduled_time = timezone.now() + timedelta(hours=2)

queued_email = email_service.queue_email(
    recipient=user,
    email_type='enrollment',
    scheduled_at=scheduled_time,
    context={'course': course},
    priority='high'
)
```

## Email Templates

### Template Variables

All email templates have access to these variables:

- `user` - The recipient user object
- `course` - Related course object (if applicable)
- `enrollment` - Related enrollment object (if applicable)
- `payment` - Related payment object (if applicable)
- `site_name` - Site name from settings
- `site_url` - Site URL from settings

### Template Types

1. **enrollment** - Course enrollment confirmation
2. **demo_completed** - Post-demo class follow-up
3. **payment_confirmation** - Payment success confirmation
4. **weekly_progress** - Weekly progress report
5. **new_content** - New content notification

### Customizing Templates

You can customize email templates through the Django admin interface:

1. Go to `/admin/email_automation/emailtemplate/`
2. Select the template you want to edit
3. Modify the subject, HTML content, or text content
4. Save changes

Templates use Django template syntax:
```html
<h2>Welcome {{ user.first_name|default:user.username }}!</h2>
<p>You've enrolled in {{ course.title }} for ${{ course.price }}</p>
```

## User Email Preferences

Users can manage their email preferences through the `EmailPreference` model:

```python
from email_automation.models import EmailPreference

# Get user preferences
try:
    prefs = EmailPreference.objects.get(user=user)
except EmailPreference.DoesNotExist:
    prefs = EmailPreference.objects.create(user=user)

# Update preferences
prefs.progress_emails = False  # Disable progress emails
prefs.save()

# Unsubscribe from all emails
prefs.unsubscribe()
```

## Monitoring and Logging

### Email Logs

All sent emails are logged in the `EmailLog` model with the following information:
- Recipient
- Email type
- Subject and content
- Status (pending, sent, failed, delivered, opened, clicked)
- Timestamps
- Error messages (if any)

### Admin Interface

Monitor email activity through Django admin:
- `/admin/email_automation/emaillog/` - View all email logs
- `/admin/email_automation/emailqueue/` - View queued emails
- `/admin/email_automation/weeklyprogressreport/` - View progress reports

### Celery Monitoring

Monitor Celery tasks:

```bash
# View active tasks
celery -A lms inspect active

# View scheduled tasks
celery -A lms inspect scheduled

# View task statistics
celery -A lms inspect stats
```

## Scheduled Tasks

The system runs these scheduled tasks:

1. **Weekly Progress Reports** - Every Monday at 9 AM
2. **Email Queue Processing** - Every 5 minutes
3. **Email Log Cleanup** - Daily at 2 AM (removes logs older than 90 days)

## Troubleshooting

### Common Issues

1. **Emails not sending**
   - Check Celery worker is running
   - Verify email configuration in settings
   - Check email logs for error messages

2. **Templates not found**
   - Run `python manage.py setup_email_automation`
   - Check templates exist in admin interface

3. **Celery tasks not running**
   - Ensure Redis is running
   - Check Celery beat scheduler is running
   - Verify task scheduling in `lms/celery.py`

### Debug Commands

```bash
# Test email sending
python manage.py shell
>>> from email_automation.services import EmailService
>>> from django.contrib.auth import get_user_model
>>> User = get_user_model()
>>> user = User.objects.first()
>>> service = EmailService()
>>> service.send_email(user, 'enrollment', course=None)

# Check Celery tasks
celery -A lms inspect registered

# Test task execution
python manage.py shell
>>> from email_automation.tasks import send_enrollment_email
>>> send_enrollment_email.delay(1, 1, 1)
```

## Security Considerations

1. **Email Preferences** - Always check user preferences before sending emails
2. **Rate Limiting** - Consider implementing rate limiting for bulk emails
3. **Unsubscribe Links** - Add unsubscribe functionality to email templates
4. **Data Privacy** - Email logs contain personal data, ensure proper data retention policies

## Performance Optimization

1. **Bulk Operations** - Use bulk email sending for multiple recipients
2. **Queue Management** - Use priority queues for urgent emails
3. **Database Indexing** - Add indexes on frequently queried fields
4. **Email Throttling** - Implement throttling to avoid overwhelming email servers

## Integration with External Services

### SendGrid Integration

For advanced features like email tracking, analytics, and better deliverability:

```bash
pip install sendgrid
```

```python
# Custom email backend for SendGrid
# Create email_automation/backends.py
import sendgrid
from sendgrid.helpers.mail import Mail
from django.core.mail.backends.base import BaseEmailBackend

class SendGridBackend(BaseEmailBackend):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sg = sendgrid.SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)
    
    def send_messages(self, email_messages):
        # Implementation for SendGrid API
        pass
```

### Mailgun Integration

Similar to SendGrid, you can create custom backends for other email services.

## Future Enhancements

1. **Email Analytics** - Track open rates, click rates, and engagement
2. **A/B Testing** - Test different email templates and content
3. **Personalization** - Advanced personalization based on user behavior
4. **Email Campaigns** - Support for marketing email campaigns
5. **SMS Integration** - Add SMS notifications alongside emails
6. **Webhook Support** - Handle email delivery webhooks from email providers

## Support

For issues or questions about the email automation system:

1. Check the Django admin interface for email logs and errors
2. Review Celery worker logs for task execution issues
3. Verify email configuration and credentials
4. Test email sending in Django shell for debugging

The system is designed to be robust and handle failures gracefully, with automatic retries and comprehensive logging for troubleshooting.