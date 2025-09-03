# live_classes/utils.py

from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from datetime import datetime, timedelta, date
from calendar import monthrange

from .models import LiveClassSchedule, LiveClassSubscription, LiveClassSession
from notifications.models import Notification


def calculate_subscription_dates(schedule, subscription_type, start_date=None):
    """Calculate subscription start and end dates"""
    if start_date is None:
        start_date = timezone.now().date()
    
    if subscription_type == 'weekly':
        end_date = start_date + timedelta(days=7)
        classes_included = schedule.classes_per_week
    else:  # monthly
        # Calculate end of month
        year = start_date.year
        month = start_date.month
        if month == 12:
            next_month = 1
            next_year = year + 1
        else:
            next_month = month + 1
            next_year = year
        
        end_date = date(next_year, next_month, 1) - timedelta(days=1)
        
        # Calculate classes in the month
        days_in_month = (end_date - start_date).days + 1
        weeks_in_period = days_in_month // 7
        classes_included = schedule.classes_per_week * weeks_in_period
        
        # Add remaining days
        remaining_days = days_in_month % 7
        if remaining_days > 0:
            # Count how many class days fall in remaining days
            additional_classes = 0
            for day_offset in range(remaining_days):
                check_date = start_date + timedelta(days=weeks_in_period * 7 + day_offset)
                day_name = check_date.strftime('%A').lower()
                if day_name in schedule.class_days:
                    additional_classes += 1
            classes_included += additional_classes
    
    return start_date, end_date, classes_included


def check_subscription_validity(schedule, student):
    """Check if student has valid subscription for the schedule"""
    active_subscription = LiveClassSubscription.objects.filter(
        schedule=schedule,
        student=student,
        status='active'
    ).first()
    
    if not active_subscription:
        return False, "No active subscription found"
    
    if not active_subscription.is_valid():
        return False, "Subscription has expired"
    
    if not active_subscription.can_attend_class():
        return False, "Maximum classes for this subscription period reached"
    
    return True, "Valid subscription"


def create_subscription_payment_record(subscription, payment_data):
    """Create payment record for subscription"""
    from .models import LiveClassPayment
    
    payment = LiveClassPayment.objects.create(
        subscription=subscription,
        student=subscription.student,
        schedule=subscription.schedule,
        amount=subscription.amount_paid,
        payment_method=payment_data.get('payment_method', ''),
        transaction_reference=payment_data.get('transaction_id', ''),
        status='pending',
        gateway_response=payment_data.get('gateway_response', {})
    )
    
    return payment


def send_schedule_creation_notification(schedule):
    """Send notifications when new schedule is created"""
    # Notify student
    student_message = f"""
    Hello {schedule.student.full_name},
    
    A new live class schedule has been created for you:
    
    Subject: {schedule.subject}
    Teacher: {schedule.teacher.full_name}
    Classes per week: {schedule.classes_per_week}
    Days: {', '.join(schedule.class_days).title()}
    Duration: {schedule.class_duration} minutes
    
    Weekly Payment: ${schedule.weekly_payment}
    Monthly Payment: ${schedule.monthly_payment}
    
    Your first class will be a FREE demo class. Please join at the scheduled time.
    
    Best regards,
    Your LMS Team
    """
    
    send_mail(
        f'New Live Class Schedule - {schedule.subject}',
        student_message,
        settings.DEFAULT_FROM_EMAIL,
        [schedule.student.user.email],
        fail_silently=True,
    )
    
    # Notify admin
    Notification.objects.create(
        recipient_id=1,  # Admin
        notification_type='general',
        title='New Live Class Schedule Created',
        message=f'{schedule.teacher.full_name} created schedule for {schedule.subject} with {schedule.student.full_name}'
    )


def send_payment_confirmation_email(payment):
    """Send payment confirmation email"""
    subscription = payment.subscription
    schedule = subscription.schedule
    
    message = f"""
    Dear {subscription.student.full_name},
    
    Your payment has been successfully processed!
    
    Payment Details:
    - Amount: ${payment.amount}
    - Transaction ID: {payment.transaction_reference}
    - Payment Method: {payment.payment_method}
    
    Subscription Details:
    - Subject: {schedule.subject}
    - Teacher: {schedule.teacher.full_name}
    - Type: {subscription.subscription_type.title()}
    - Classes Included: {subscription.classes_included}
    - Valid From: {subscription.start_date}
    - Valid Until: {subscription.end_date}
    
    You can now join your scheduled live classes through your dashboard.
    
    Best regards,
    Your LMS Team
    """
    
    send_mail(
        f'Payment Confirmation - {schedule.subject}',
        message,
        settings.DEFAULT_FROM_EMAIL,
        [subscription.student.user.email],
        fail_silently=True,
    )


def get_schedule_statistics(schedule):
    """Get detailed statistics for a schedule"""
    sessions = schedule.sessions.all()
    subscriptions = schedule.subscriptions.all()
    
    stats = {
        'total_sessions': sessions.count(),
        'completed_sessions': sessions.filter(status='completed').count(),
        'missed_sessions': sessions.filter(status='missed').count(),
        'cancelled_sessions': sessions.filter(status='cancelled').count(),
        'demo_completed': schedule.demo_completed,
        'total_subscriptions': subscriptions.count(),
        'active_subscriptions': subscriptions.filter(status='active').count(),
        'expired_subscriptions': subscriptions.filter(status='expired').count(),
        'total_revenue': sum(sub.amount_paid for sub in subscriptions),
        'average_attendance_rate': 0
    }
    
    # Calculate attendance rate
    if stats['total_sessions'] > 0:
        stats['average_attendance_rate'] = (
            stats['completed_sessions'] / stats['total_sessions'] * 100
        )
    
    return stats


def get_teacher_analytics(teacher_profile, date_range=None):
    """Get analytics for teacher's live classes"""
    schedules = teacher_profile.live_schedules.all()
    
    if date_range:
        start_date, end_date = date_range
        sessions = LiveClassSession.objects.filter(
            schedule__teacher=teacher_profile,
            scheduled_datetime__date__range=[start_date, end_date]
        )
        subscriptions = LiveClassSubscription.objects.filter(
            schedule__teacher=teacher_profile,
            created_at__date__range=[start_date, end_date]
        )
    else:
        sessions = LiveClassSession.objects.filter(schedule__teacher=teacher_profile)
        subscriptions = LiveClassSubscription.objects.filter(schedule__teacher=teacher_profile)
    
    analytics = {
        'total_schedules': schedules.count(),
        'active_schedules': schedules.filter(is_active=True).count(),
        'total_students': schedules.values('student').distinct().count(),
        'total_sessions': sessions.count(),
        'completed_sessions': sessions.filter(status='completed').count(),
        'total_revenue': sum(sub.amount_paid for sub in subscriptions),
        'demo_sessions': sessions.filter(is_demo=True).count(),
        'demo_conversion_rate': 0
    }
    
    # Calculate demo conversion rate
    if analytics['demo_sessions'] > 0:
        converted_demos = schedules.filter(demo_completed=True, subscriptions__isnull=False).count()
        analytics['demo_conversion_rate'] = (converted_demos / analytics['demo_sessions'] * 100)
    
    return analytics


def get_student_analytics(student_profile, date_range=None):
    """Get analytics for student's live classes"""
    schedules = student_profile.live_schedules.all()
    
    if date_range:
        start_date, end_date = date_range
        sessions = LiveClassSession.objects.filter(
            schedule__student=student_profile,
            scheduled_datetime__date__range=[start_date, end_date]
        )
        subscriptions = LiveClassSubscription.objects.filter(
            student=student_profile,
            created_at__date__range=[start_date, end_date]
        )
    else:
        sessions = LiveClassSession.objects.filter(schedule__student=student_profile)
        subscriptions = LiveClassSubscription.objects.filter(student=student_profile)
    
    analytics = {
        'total_schedules': schedules.count(),
        'active_schedules': schedules.filter(is_active=True).count(),
        'total_teachers': schedules.values('teacher').distinct().count(),
        'total_sessions': sessions.count(),
        'attended_sessions': sessions.filter(status='completed', student_joined=True).count(),
        'missed_sessions': sessions.filter(status='missed').count(),
        'total_spent': sum(sub.amount_paid for sub in subscriptions),
        'active_subscriptions': subscriptions.filter(status='active').count(),
        'attendance_rate': 0
    }
    
    # Calculate attendance rate
    if analytics['total_sessions'] > 0:
        analytics['attendance_rate'] = (
            analytics['attended_sessions'] / analytics['total_sessions'] * 100
        )
    
    return analytics


def validate_schedule_data(data):
    """Validate schedule creation data"""
    errors = {}
    
    # Validate class days
    valid_days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    if 'class_days' in data:
        for day in data['class_days']:
            if day not in valid_days:
                errors.setdefault('class_days', []).append(f'Invalid day: {day}')
    
    # Validate class times format
    if 'class_times' in data:
        for day, time_str in data['class_times'].items():
            try:
                datetime.strptime(time_str, '%H:%M')
            except ValueError:
                errors.setdefault('class_times', []).append(f'Invalid time format for {day}: {time_str}')
    
    # Validate consistency between days and times
    if 'class_days' in data and 'class_times' in data:
        for day in data['class_days']:
            if day not in data['class_times']:
                errors.setdefault('class_times', []).append(f'Missing time for {day}')
    
    # Validate payment amounts
    if 'weekly_payment' in data and data['weekly_payment'] <= 0:
        errors['weekly_payment'] = 'Weekly payment must be greater than 0'
    
    if 'monthly_payment' in data and data['monthly_payment'] <= 0:
        errors['monthly_payment'] = 'Monthly payment must be greater than 0'
    
    return errors


def generate_class_schedule_preview(schedule_data, weeks=4):
    """Generate a preview of class schedule for the next few weeks"""
    preview = []
    
    start_date = schedule_data.get('start_date', timezone.now().date())
    class_days = schedule_data.get('class_days', [])
    class_times = schedule_data.get('class_times', {})
    
    current_date = start_date
    end_date = start_date + timedelta(weeks=weeks)
    
    while current_date <= end_date:
        day_name = current_date.strftime('%A').lower()
        
        if day_name in class_days and day_name in class_times:
            time_str = class_times[day_name]
            class_time = datetime.strptime(time_str, '%H:%M').time()
            class_datetime = datetime.combine(current_date, class_time)
            
            preview.append({
                'date': current_date.isoformat(),
                'time': time_str,
                'datetime': class_datetime.isoformat(),
                'day': day_name.title()
            })
        
        current_date += timedelta(days=1)
    
    return preview