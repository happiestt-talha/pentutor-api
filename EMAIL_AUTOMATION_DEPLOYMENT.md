# Email Automation System - Deployment Guide

## 🚀 Quick Start

### 1. Installation & Setup

The email automation system has been successfully integrated into your Django LMS project. Here's how to deploy and use it:

```bash
# 1. Activate virtual environment
source venv/bin/activate

# 2. Install dependencies (already done)
pip install -r requirements.txt

# 3. Run migrations (already done)
python manage.py migrate

# 4. Initialize email templates and user preferences
python manage.py setup_email_automation --create-preferences
```

### 2. Email Provider Configuration

#### Option A: Gmail SMTP (Recommended for testing)
```python
# In settings.py
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'  # Use App Password, not regular password
DEFAULT_FROM_EMAIL = 'your-email@gmail.com'
```

#### Option B: SendGrid
```python
# Install sendgrid
pip install sendgrid

# In settings.py
EMAIL_BACKEND = 'sendgrid_backend.SendgridBackend'
SENDGRID_API_KEY = 'your-sendgrid-api-key'
DEFAULT_FROM_EMAIL = 'noreply@yourdomain.com'
```

#### Option C: Mailgun
```python
# Install django-anymail
pip install django-anymail[mailgun]

# In settings.py
EMAIL_BACKEND = 'anymail.backends.mailgun.EmailBackend'
ANYMAIL = {
    'MAILGUN_API_KEY': 'your-mailgun-api-key',
    'MAILGUN_SENDER_DOMAIN': 'yourdomain.com',
}
DEFAULT_FROM_EMAIL = 'noreply@yourdomain.com'
```

### 3. Redis & Celery Setup

#### Install Redis
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install redis-server
sudo systemctl start redis
sudo systemctl enable redis

# macOS
brew install redis
brew services start redis

# Check Redis is running
redis-cli ping  # Should return "PONG"
```

#### Start Celery Services
```bash
# Terminal 1: Start Celery Worker
celery -A lms worker -l info

# Terminal 2: Start Celery Beat (for scheduled tasks)
celery -A lms beat -l info

# Optional: Start Celery Flower (monitoring)
pip install flower
celery -A lms flower
```

### 4. Testing the System

```bash
# Run the test script to verify everything works
python test_email_system_simple.py
```

## 📧 Email Scenarios

### 1. Course Enrollment Email
**Trigger**: When a student enrolls in a course
**Message**: "🎉 Congratulations! You've successfully joined our course. Please proceed with the payment. The course fee is [amount]."

### 2. Post-Demo Class Email
**Trigger**: When a student's demo class participation is marked as completed
**Message**: "You have successfully attended your demo class. To continue the course, please complete the payment."

### 3. Post-Payment Confirmation Email
**Trigger**: When payment status is updated to 'completed'
**Message**: "✅ Payment received! Welcome officially to the course. We wish you a great learning journey!"

### 4. Weekly Progress Email
**Trigger**: Every Monday at 9 AM (automated)
**Message**: "📈 Your weekly progress: You've completed 3 out of 10 modules this week. Keep it up!"

### 5. New Content Notification
**Trigger**: When new videos or lessons are added to a course
**Message**: "🎥 New content added to your course! Check it out in your LMS dashboard."

## 🔧 API Endpoints

### Base URL: `/api/email-automation/`

#### Test Enrollment Email
```bash
POST /api/email-automation/test-enrollment-email/
{
    "user_id": 1,
    "course_id": 1
}
```

#### Test Payment Email
```bash
POST /api/email-automation/test-payment-email/
{
    "user_id": 1,
    "course_id": 1
}
```

#### Trigger Weekly Reports
```bash
POST /api/email-automation/trigger-weekly-reports/
```

#### Test New Content Email
```bash
POST /api/email-automation/test-new-content-email/
{
    "course_id": 1,
    "content_type": "video",
    "content_title": "Advanced Django Concepts"
}
```

#### Get Email Logs
```bash
GET /api/email-automation/email-logs/
```

#### Manage Email Preferences
```bash
# Get preferences
GET /api/email-automation/preferences/

# Update preferences
POST /api/email-automation/preferences/
{
    "enrollment_emails": true,
    "progress_emails": false,
    "payment_emails": true,
    "content_emails": true,
    "demo_emails": true
}
```

## 🎛️ Admin Interface

Access the Django admin at `/admin/` to manage:

- **Email Templates**: Customize email content and subjects
- **Email Logs**: View all sent emails and their status
- **Email Preferences**: Manage user email preferences
- **Weekly Progress Reports**: View generated reports
- **Email Queue**: Monitor queued emails

## 📊 Monitoring & Logs

### Email Logs
All emails are logged with:
- Recipient information
- Email type and content
- Send status (pending, sent, failed, delivered, opened, clicked)
- Timestamps for tracking

### Celery Monitoring
Use Celery Flower for real-time monitoring:
```bash
celery -A lms flower
# Access at http://localhost:5555
```

### Django Logs
Email system logs are available in Django's logging system:
```python
# In settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'email_automation.log',
        },
    },
    'loggers': {
        'email_automation': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

## 🔄 Scheduled Tasks

The system includes these automated tasks:

### Weekly Progress Reports
- **Schedule**: Every Monday at 9:00 AM
- **Task**: `generate_weekly_progress_reports`
- **Description**: Generates and sends progress summaries to all enrolled students

### Email Queue Processing
- **Schedule**: Every 5 minutes
- **Task**: `process_email_queue`
- **Description**: Processes any queued emails that failed to send

### Email Log Cleanup
- **Schedule**: Daily at 2:00 AM
- **Task**: `cleanup_old_email_logs`
- **Description**: Removes email logs older than 90 days

## 🛠️ Customization

### Email Templates
Edit templates in the Django admin or programmatically:

```python
from email_automation.models import EmailTemplate

# Update enrollment email template
template = EmailTemplate.objects.get(email_type='enrollment')
template.subject = 'Welcome to {{ course.title }}!'
template.html_content = '''
<h1>Welcome {{ user.first_name }}!</h1>
<p>You've enrolled in {{ course.title }}</p>
<p>Course fee: ${{ course.price }}</p>
'''
template.save()
```

### Custom Email Types
Add new email types by extending the system:

```python
# In email_automation/models.py
EMAIL_TYPES = [
    # ... existing types ...
    ('course_reminder', 'Course Reminder'),
    ('certificate_ready', 'Certificate Ready'),
]
```

### Custom Triggers
Create custom signal handlers:

```python
from django.db.models.signals import post_save
from django.dispatch import receiver
from .tasks import send_custom_email

@receiver(post_save, sender=YourModel)
def handle_custom_event(sender, instance, created, **kwargs):
    if created:
        send_custom_email.delay(instance.user.id, 'custom_type')
```

## 🚨 Troubleshooting

### Common Issues

#### 1. Emails not sending
- Check Redis connection: `redis-cli ping`
- Verify Celery worker is running
- Check email backend configuration
- Review Django logs for errors

#### 2. Templates not rendering
- Verify template syntax
- Check context variables match template
- Test template rendering in Django shell

#### 3. Scheduled tasks not running
- Ensure Celery Beat is running
- Check beat schedule in settings
- Verify timezone settings

#### 4. High email volume
- Implement rate limiting
- Use email queuing system
- Consider background processing

### Debug Commands

```bash
# Test email sending
python manage.py shell
>>> from email_automation.services import EmailService
>>> service = EmailService()
>>> # Test email sending...

# Check Celery tasks
celery -A lms inspect active
celery -A lms inspect scheduled

# Monitor Redis
redis-cli monitor
```

## 🔐 Security Considerations

1. **Email Authentication**: Use App Passwords for Gmail, API keys for other providers
2. **Rate Limiting**: Implement email rate limiting to prevent abuse
3. **Unsubscribe Links**: Include unsubscribe functionality in all emails
4. **Data Privacy**: Respect user preferences and GDPR compliance
5. **Secure Storage**: Store email credentials securely (environment variables)

## 📈 Performance Optimization

1. **Batch Processing**: Process emails in batches to improve performance
2. **Caching**: Cache email templates and user preferences
3. **Database Indexing**: Add indexes on frequently queried fields
4. **Monitoring**: Monitor email delivery rates and response times

## 🎯 Next Steps

1. **A/B Testing**: Implement email template A/B testing
2. **Analytics**: Add email open/click tracking
3. **Personalization**: Enhance email personalization
4. **Integration**: Integrate with CRM systems
5. **Mobile**: Optimize emails for mobile devices

---

## 📞 Support

For issues or questions:
1. Check the troubleshooting section above
2. Review Django and Celery logs
3. Test individual components using the provided scripts
4. Consult the Django and Celery documentation

The email automation system is now fully integrated and ready for production use!