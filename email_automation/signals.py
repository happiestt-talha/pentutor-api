# email_automation/signals.py

import logging
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from courses.models import Enrollment, Video
from payments.models import Payment
from meetings.models import Participant
from .tasks import (
    send_enrollment_email,
    send_payment_confirmation_email,
    send_demo_completed_email,
    send_new_content_notification
)

User = get_user_model()
logger = logging.getLogger(__name__)


@receiver(post_save, sender=Enrollment)
def handle_enrollment_created(sender, instance, created, **kwargs):
    """
    Send enrollment email when a student enrolls in a course
    """
    if created:
        logger.info(f"New enrollment created: {instance.student.email} -> {instance.course.title}")
        
        # Trigger enrollment email task
        send_enrollment_email(
            user_id=instance.student.id,
            course_id=instance.course.id,
            enrollment_id=instance.id
        )


@receiver(post_save, sender=Payment)
def handle_payment_success(sender, instance, created, **kwargs):
    """
    Send payment confirmation email when payment is successful
    """
    # Check if payment status changed to successful
    if instance.is_successful:
        # Check if this is a status change (not a new creation with success=True)
        if not created:
            try:
                # Get the previous state from database
                old_instance = Payment.objects.get(pk=instance.pk)
                if hasattr(old_instance, '_state') and not old_instance.is_successful:
                    # Payment status changed from unsuccessful to successful
                    logger.info(f"Payment successful: {instance.user.email} -> {instance.course.title}")
                    
                    send_payment_confirmation_email(
                        user_id=instance.user.id,
                        payment_id=instance.id
                    )
            except Payment.DoesNotExist:
                pass
        elif created and instance.is_successful:
            # New payment created with success=True
            logger.info(f"New successful payment: {instance.user.email} -> {instance.course.title}")
            
            send_payment_confirmation_email.delay(
                user_id=instance.user.id,
                payment_id=instance.id
            )


@receiver(post_save, sender=Participant)
def handle_demo_class_completion(sender, instance, created, **kwargs):
    """
    Send demo completion email when participant leaves a demo meeting
    """
    # Check if participant left the meeting (left_at is set)
    if instance.left_at and instance.meeting.course:
        # Check if this is a demo meeting (assuming 'demo' in title indicates demo)
        if 'demo' in instance.meeting.title.lower():
            logger.info(f"Demo class completed: {instance.user.email} -> {instance.meeting.course.title}")
            
            send_demo_completed_email.delay(
                user_id=instance.user.id,
                course_id=instance.meeting.course.id,
                meeting_id=instance.meeting.id
            )


# @receiver(post_save, sender=Video)
# def handle_new_video_added(sender, instance, created, **kwargs):
#     """
#     Send new content notification when a video is added to a course
#     """
#     if created:
#         logger.info(f"New video added to course: {instance.course.title} - {instance.title}")
        
#         # Send notification to all enrolled students
#         send_new_content_notification.delay(
#             course_id=instance.course.id,
#             content_description=f"New video: {instance.title}"
#         )


# You can add more signal handlers for other models like Quiz, Assignment, etc.
# For example:

# @receiver(post_save, sender=Quiz)
# def handle_new_quiz_added(sender, instance, created, **kwargs):
#     """Send notification when a new quiz is added"""
#     if created:
#         send_new_content_notification.delay(
#             course_id=instance.course.id,
#             content_description=f"New quiz: {instance.title}"
#         )

# @receiver(post_save, sender=Assignment)
# def handle_new_assignment_added(sender, instance, created, **kwargs):
#     """Send notification when a new assignment is added"""
#     if created:
#         send_new_content_notification.delay(
#             course_id=instance.course.id,
#             content_description=f"New assignment: {instance.title}"
#         )