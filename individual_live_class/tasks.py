# live_classes/tasks.py

from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from datetime import datetime, timedelta

from .models import LiveClassPayment, LiveClassSchedule, LiveClassSubscription, LiveClassSession
from notifications.models import Notification


@shared_task
def create_scheduled_sessions():
    """Create sessions for all active schedules for the next week"""
    active_schedules = LiveClassSchedule.objects.filter(is_active=True)
    
    for schedule in active_schedules:
        # Create sessions for the next 7 days
        for i in range(7):
            target_date = timezone.now().date() + timedelta(days=i)
            day_name = target_date.strftime('%A').lower()
            
            if day_name in schedule.class_days:
                class_time_str = schedule.class_times.get(day_name)
                if class_time_str:
                    class_time = datetime.strptime(class_time_str, '%H:%M').time()
                    scheduled_datetime = datetime.combine(target_date, class_time)
                    scheduled_datetime = timezone.make_aware(scheduled_datetime)
                    
                    # Check if session already exists
                    if not LiveClassSession.objects.filter(
                        schedule=schedule,
                        scheduled_datetime=scheduled_datetime
                    ).exists():
                        
                        # Determine if this is a demo or paid session
                        is_demo = not schedule.demo_completed
                        
                        # Get active subscription for paid sessions
                        subscription = None
                        if not is_demo:
                            subscription = LiveClassSubscription.objects.filter(
                                schedule=schedule,
                                status='active',
                                start_date__lte=target_date,
                                end_date__gte=target_date
                            ).first()
                        
                        session = LiveClassSession.objects.create(
                            schedule=schedule,
                            subscription=subscription,
                            scheduled_datetime=scheduled_datetime,
                            duration=schedule.class_duration,
                            is_demo=is_demo
                        )
                        
                        print(f"Created session: {session}")


@shared_task
def check_expired_subscriptions():
    """Check and update expired subscriptions"""
    expired_subscriptions = LiveClassSubscription.objects.filter(
        status='active',
        end_date__lt=timezone.now().date()
    )
    
    for subscription in expired_subscriptions:
        subscription.status = 'expired'
        subscription.save()
        
        # Send notification to student
        send_subscription_expiry_email.delay(subscription.id)
        
        # Notify admin
        Notification.objects.create(
            recipient_id=1,  # Admin
            notification_type='general',
            title='Subscription Expired',
            message=f'Subscription expired for {subscription.student.full_name} - {subscription.schedule.subject}'
        )


@shared_task
def send_subscription_expiry_email(subscription_id):
    """Send email to student when subscription expires"""
    try:
        subscription = LiveClassSubscription.objects.get(id=subscription_id)
        
        subject = f'Live Class Subscription Expired - {subscription.schedule.subject}'
        message = f"""
        Dear {subscription.student.full_name},
        
        Your live class subscription for {subscription.schedule.subject} has expired.
        
        To continue attending classes, please renew your subscription:
        - Weekly Payment: ${subscription.schedule.weekly_payment}
        - Monthly Payment: ${subscription.schedule.monthly_payment}
        
        Teacher: {subscription.schedule.teacher.full_name}
        Classes per week: {subscription.schedule.classes_per_week}
        
        Please contact support or renew through the app to continue your classes.
        
        Best regards,
        Your LMS Team
        """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [subscription.student.user.email],
            fail_silently=False,
        )
        
    except LiveClassSubscription.DoesNotExist:
        print(f"Subscription {subscription_id} not found")


@shared_task
def send_class_reminder():
    """Send reminder for upcoming classes (1 hour before)"""
    reminder_time = timezone.now() + timedelta(hours=1)
    
    upcoming_sessions = LiveClassSession.objects.filter(
        scheduled_datetime__range=[
            timezone.now(),
            reminder_time
        ],
        status='scheduled'
    )
    
    for session in upcoming_sessions:
        # Send to student
        if session.schedule.student.user.email:
            send_class_reminder_email.delay(
                session.id, 
                session.schedule.student.user.email,
                'student'
            )
        
        # Send to teacher
        if session.schedule.teacher.user.email:
            send_class_reminder_email.delay(
                session.id,
                session.schedule.teacher.user.email,
                'teacher'
            )


@shared_task
def send_class_reminder_email(session_id, email, user_type):
    """Send class reminder email"""
    try:
        session = LiveClassSession.objects.get(id=session_id)
        
        subject = f'Live Class Reminder - {session.schedule.subject}'
        
        if user_type == 'student':
            recipient_name = session.schedule.student.full_name
            other_person = f"Teacher: {session.schedule.teacher.full_name}"
        else:
            recipient_name = session.schedule.teacher.full_name
            other_person = f"Student: {session.schedule.student.full_name}"
        
        message = f"""
        Dear {recipient_name},
        
        This is a reminder for your upcoming live class:
        
        Subject: {session.schedule.subject}
        {other_person}
        Scheduled Time: {session.scheduled_datetime.strftime('%Y-%m-%d %H:%M')}
        Duration: {session.duration} minutes
        {'Demo Class: FREE' if session.is_demo else ''}
        
        Please join the class on time through your dashboard.
        
        Best regards,
        Your LMS Team
        """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
        
    except LiveClassSession.DoesNotExist:
        print(f"Session {session_id} not found")


@shared_task
def mark_missed_sessions():
    """Mark sessions as missed if no one joined within 15 minutes"""
    cutoff_time = timezone.now() - timedelta(minutes=15)
    
    missed_sessions = LiveClassSession.objects.filter(
        scheduled_datetime__lt=cutoff_time,
        status='scheduled',
        student_joined=False,
        teacher_joined=False
    )
    
    for session in missed_sessions:
        session.status = 'missed'
        session.save()
        
        # Notify admin
        Notification.objects.create(
            recipient_id=1,  # Admin
            notification_type='general',
            title='Class Missed',
            message=f'Class missed: {session.schedule.subject} - {session.scheduled_datetime.strftime("%Y-%m-%d %H:%M")}'
        )


@shared_task
def cleanup_old_sessions():
    """Clean up old session data (older than 3 months)"""
    cutoff_date = timezone.now() - timedelta(days=90)
    
    old_sessions = LiveClassSession.objects.filter(
        scheduled_datetime__lt=cutoff_date,
        status__in=['completed', 'missed', 'cancelled']
    )
    
    count = old_sessions.count()
    old_sessions.delete()
    
    print(f"Cleaned up {count} old sessions")


@shared_task
def generate_monthly_reports():
    """Generate monthly reports for admin"""
    from django.db.models import Count, Sum
    
    current_month = timezone.now().replace(day=1)
    last_month = (current_month - timedelta(days=1)).replace(day=1)
    
    # Get statistics for last month
    schedules_created = LiveClassSchedule.objects.filter(
        created_at__gte=last_month,
        created_at__lt=current_month
    ).count()
    
    subscriptions_created = LiveClassSubscription.objects.filter(
        created_at__gte=last_month,
        created_at__lt=current_month
    ).count()
    
    total_revenue = LiveClassPayment.objects.filter(
        completed_at__gte=last_month,
        completed_at__lt=current_month,
        status='completed'
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    sessions_completed = LiveClassSession.objects.filter(
        scheduled_datetime__gte=last_month,
        scheduled_datetime__lt=current_month,
        status='completed'
    ).count()
    
    # Create notification for admin
    Notification.objects.create(
        recipient_id=1,  # Admin
        notification_type='general',
        title='Monthly Live Classes Report',
        message=f"""
        Live Classes Report for {last_month.strftime('%B %Y')}:
        
        - New Schedules Created: {schedules_created}
        - New Subscriptions: {subscriptions_created}
        - Total Revenue: ${total_revenue}
        - Sessions Completed: {sessions_completed}
        
        Check admin panel for detailed analytics.
        """
    )