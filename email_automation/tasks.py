# email_automations/tasks.py
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

from celery import shared_task
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db.models import Count, Q

from courses.models import Course, Enrollment, Progress, Video
from meetings.models import Meeting, Participant
from payments.models import Payment
from .models import EmailQueue, WeeklyProgressReport, EmailPreference
from .services import EmailService

User = get_user_model()
logger = logging.getLogger(__name__)


@shared_task
def send_enrollment_email(user_id: int, course_id: int, enrollment_id: int):
    """
    Send enrollment confirmation email when a student enrolls in a course
    """
    try:
        user = User.objects.get(id=user_id)
        course = Course.objects.get(id=course_id)
        enrollment = Enrollment.objects.get(id=enrollment_id)
        
        email_service = EmailService()
        success = email_service.send_email(
            recipient=user,
            email_type='enrollment',
            course=course,
            enrollment=enrollment
        )
        
        logger.info(f"Enrollment email sent to {user.email} for course {course.title}: {success}")
        return success
        
    except Exception as e:
        logger.error(f"Failed to send enrollment email: {str(e)}")
        return False


@shared_task
def send_demo_completed_email(user_id: int, course_id: int, meeting_id: int):
    """
    Send email after student completes a demo class
    """
    try:
        user = User.objects.get(id=user_id)
        course = Course.objects.get(id=course_id)
        meeting = Meeting.objects.get(id=meeting_id)
        
        # Check if the meeting was actually a demo (you might need to add a field to identify demo meetings)
        # For now, we'll assume any meeting with 'demo' in the title is a demo
        if 'demo' not in meeting.title.lower():
            logger.info(f"Meeting {meeting.title} is not a demo class, skipping email")
            return False
        
        email_service = EmailService()
        success = email_service.send_email(
            recipient=user,
            email_type='demo_completed',
            course=course,
            context={'meeting': meeting}
        )
        
        logger.info(f"Demo completed email sent to {user.email} for course {course.title}: {success}")
        return success
        
    except Exception as e:
        logger.error(f"Failed to send demo completed email: {str(e)}")
        return False


@shared_task
def send_payment_confirmation_email(user_id: int, payment_id: int):
    """
    Send payment confirmation email when payment is successful
    """
    try:
        user = User.objects.get(id=user_id)
        payment = Payment.objects.get(id=payment_id)
        course = payment.course
        
        if not payment.is_successful:
            print("email is not send")
            logger.info(f"Payment {payment.id} is not successful, skipping email")
            return False
        
        email_service = EmailService()
        print("actully send")
        success = email_service.send_email(
            recipient=user,
            email_type='payment_confirmation',
            course=course,
            payment=payment
        )
        print("last send")
        
        logger.info(f"Payment confirmation email sent to {user.email} for course {course.title}: {success}")
        return success
        
    except Exception as e:
        logger.error(f"Failed to send payment confirmation email: {str(e)}")
        return False


@shared_task
def generate_weekly_progress_reports():
    """
    Generate weekly progress reports for all enrolled students
    """
    try:
        # Get current week boundaries
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        
        # Get all active enrollments
        enrollments = Enrollment.objects.filter(
            is_completed=False,
            course__is_active=True
        ).select_related('student', 'course')
        
        reports_created = 0
        
        for enrollment in enrollments:
            # Check if report already exists for this week
            if WeeklyProgressReport.objects.filter(
                user=enrollment.student,
                course=enrollment.course,
                week_start=week_start
            ).exists():
                continue
            
            # Calculate progress for the week
            progress_data = calculate_weekly_progress(
                enrollment.student,
                enrollment.course,
                week_start,
                week_end
            )
            
            # Create progress report
            report = WeeklyProgressReport.objects.create(
                user=enrollment.student,
                course=enrollment.course,
                week_start=week_start,
                week_end=week_end,
                **progress_data,
                report_generated=True
            )
            
            reports_created += 1
            
            # Schedule email to be sent
            send_weekly_progress_email.delay(report.id)
        
        logger.info(f"Generated {reports_created} weekly progress reports")
        return reports_created
        
    except Exception as e:
        logger.error(f"Failed to generate weekly progress reports: {str(e)}")
        return 0


@shared_task
def send_weekly_progress_email(report_id: int):
    """
    Send weekly progress email to a student
    """
    try:
        report = WeeklyProgressReport.objects.get(id=report_id)
        
        if report.email_sent:
            logger.info(f"Progress email already sent for report {report_id}")
            return True
        
        email_service = EmailService()
        success = email_service.send_email(
            recipient=report.user,
            email_type='weekly_progress',
            course=report.course,
            context={'progress_report': report}
        )
        
        if success:
            report.email_sent = True
            report.save()
        
        logger.info(f"Weekly progress email sent to {report.user.email} for course {report.course.title}: {success}")
        return success
        
    except Exception as e:
        logger.error(f"Failed to send weekly progress email: {str(e)}")
        return False


@shared_task
def send_new_content_notification(course_id: int, content_description: str = None):
    """
    Send notification to all enrolled students when new content is added
    """
    try:
        course = Course.objects.get(id=course_id)
        
        # Get all enrolled students for this course
        enrollments = Enrollment.objects.filter(
            course=course,
            is_completed=False
        ).select_related('student')
        
        if not enrollments.exists():
            logger.info(f"No enrolled students found for course {course.title}")
            return 0
        
        email_service = EmailService()
        recipients = [enrollment.student for enrollment in enrollments]
        
        context = {}
        if content_description:
            context['new_content_description'] = content_description
        
        results = email_service.send_bulk_email(
            recipients=recipients,
            email_type='new_content',
            context=context
        )
        
        logger.info(f"New content notification sent to {results['success']} students for course {course.title}")
        return results['success']
        
    except Exception as e:
        logger.error(f"Failed to send new content notifications: {str(e)}")
        return 0


@shared_task
def process_email_queue():
    """
    Process queued emails that are ready to be sent
    """
    try:
        # Get emails that are ready to be sent
        now = timezone.now()
        queued_emails = EmailQueue.objects.filter(
            is_processed=False,
            scheduled_at__lte=now
        ).order_by('priority', 'scheduled_at')[:50]  # Process 50 at a time
        
        processed_count = 0
        
        for queued_email in queued_emails:
            try:
                email_service = EmailService()
                success = email_service.send_email(
                    recipient=queued_email.recipient,
                    email_type=queued_email.email_type,
                    context=queued_email.context_data
                )
                
                if success:
                    queued_email.is_processed = True
                    queued_email.processed_at = now
                    queued_email.save()
                    processed_count += 1
                else:
                    # Retry logic
                    queued_email.retry_count += 1
                    if queued_email.retry_count >= queued_email.max_retries:
                        queued_email.is_processed = True
                        queued_email.processed_at = now
                    else:
                        # Reschedule for retry (exponential backoff)
                        retry_delay = 2 ** queued_email.retry_count  # 2, 4, 8 minutes
                        queued_email.scheduled_at = now + timedelta(minutes=retry_delay)
                    
                    queued_email.save()
                    
            except Exception as e:
                logger.error(f"Failed to process queued email {queued_email.id}: {str(e)}")
                continue
        
        logger.info(f"Processed {processed_count} queued emails")
        return processed_count
        
    except Exception as e:
        logger.error(f"Failed to process email queue: {str(e)}")
        return 0


@shared_task
def cleanup_old_email_logs():
    """
    Clean up old email logs to prevent database bloat
    """
    try:
        # Delete email logs older than 90 days
        cutoff_date = timezone.now() - timedelta(days=90)
        
        from .models import EmailLog
        deleted_count = EmailLog.objects.filter(created_at__lt=cutoff_date).delete()[0]
        
        logger.info(f"Cleaned up {deleted_count} old email logs")
        return deleted_count
        
    except Exception as e:
        logger.error(f"Failed to cleanup old email logs: {str(e)}")
        return 0


def calculate_weekly_progress(user: User, course: Course, week_start: datetime.date, week_end: datetime.date) -> Dict[str, Any]: # type: ignore
    """
    Calculate weekly progress for a user in a course
    """
    # Convert dates to datetime for filtering
    week_start_dt = timezone.make_aware(datetime.combine(week_start, datetime.min.time()))
    week_end_dt = timezone.make_aware(datetime.combine(week_end, datetime.max.time()))
    
    # Get total counts
    total_videos = course.videos.count()
    total_quizzes = course.quizzes.count()
    total_assignments = course.assignments.count()
    
    # Get progress completed during this week
    week_progress = Progress.objects.filter(
        student=user,
        course=course,
        completed_at__gte=week_start_dt,
        completed_at__lte=week_end_dt
    )
    
    videos_completed = week_progress.filter(video__isnull=False).count()
    quizzes_completed = week_progress.filter(quiz__isnull=False).count()
    assignments_completed = week_progress.filter(assignment__isnull=False).count()
    
    return {
        'videos_completed': videos_completed,
        'total_videos': total_videos,
        'quizzes_completed': quizzes_completed,
        'total_quizzes': total_quizzes,
        'assignments_completed': assignments_completed,
        'total_assignments': total_assignments,
        'time_spent': 0,  # You can implement time tracking separately
    }


# Periodic tasks scheduling
@shared_task
def schedule_weekly_progress_emails():
    """
    Schedule weekly progress emails to be sent every Monday
    """
    return generate_weekly_progress_reports.delay()


@shared_task
def schedule_email_queue_processing():
    """
    Schedule email queue processing every 5 minutes
    """
    return process_email_queue.delay()


@shared_task
def schedule_cleanup_tasks():
    """
    Schedule cleanup tasks to run daily
    """
    return cleanup_old_email_logs.delay()