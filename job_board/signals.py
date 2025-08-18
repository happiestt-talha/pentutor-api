# job_board/signals.py

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType

from .models import JobPost, JobApplication, JobReview

# Import your notification models/functions here
# Assuming you have a notification app with these models/functions
try:
    from notifications.models import Notification
    
    NOTIFICATIONS_AVAILABLE = True
except ImportError:
    NOTIFICATIONS_AVAILABLE = False
    print("Notification app not found. Notification signals will be skipped.")


@receiver(post_save, sender=JobApplication)
def notify_student_on_application(sender, instance, created, **kwargs):
    """
    Send notification to student when a teacher applies to their job.
    """
    if not NOTIFICATIONS_AVAILABLE or not created:
        return
    
    try:
        # Create notification for the job owner (student)
        notification_data = {
            'recipient': instance.job_post.student.user,
            'title': 'New Job Application',
            'message': f'{instance.teacher.user.get_full_name() or instance.teacher.user.username} has applied to your job "{instance.job_post.title}"',
            'notification_type': 'job_application',
            'related_object_content_type': ContentType.objects.get_for_model(JobApplication),
            'related_object_id': instance.id,
            'action_url': f'/job-board/jobs/{instance.job_post.id}/applications/',
        }
        
        Notification.objects.create(**notification_data)
            
    except Exception as e:
        print(f"Failed to create job application notification: {e}")


@receiver(post_save, sender=JobApplication)
def notify_teacher_on_application_status_change(sender, instance, created, **kwargs):
    """
    Send notification to teacher when their application status changes.
    """
    if not NOTIFICATIONS_AVAILABLE or created:
        return
    
    try:
        # Check if status was changed
        if hasattr(instance, '_original_status'):
            old_status = instance._original_status
            new_status = instance.status
            
            if old_status != new_status and new_status in ['accepted', 'rejected']:
                status_messages = {
                    'accepted': f'Congratulations! Your application for "{instance.job_post.title}" has been accepted.',
                    'rejected': f'Your application for "{instance.job_post.title}" was not selected this time.',
                }
                
                notification_data = {
                    'recipient': instance.teacher.user,
                    'title': f'Application {new_status.title()}',
                    'message': status_messages.get(new_status, f'Your application status has changed to {new_status}'),
                    'notification_type': f'application_{new_status}',
                    'related_object_content_type': ContentType.objects.get_for_model(JobApplication),
                    'related_object_id': instance.id,
                    'action_url': f'/job-board/applications/{instance.id}/',
                }
                
                Notification.objects.create(**notification_data)
                    
    except Exception as e:
        print(f"Failed to create application status notification: {e}")


@receiver(post_save, sender=JobPost)
def notify_on_job_status_change(sender, instance, created, **kwargs):
    """
    Send notification when job status changes to important states.
    """
    if not NOTIFICATIONS_AVAILABLE or created:
        return
    
    try:
        # Check if status was changed to 'completed'
        if hasattr(instance, '_original_status'):
            old_status = instance._original_status
            new_status = instance.status
            
            if old_status != new_status:
                if new_status == 'completed' and instance.selected_teacher:
                    # Notify both student and teacher about completion
                    completion_message = f'The job "{instance.title}" has been marked as completed.'
                    
                    # Notify student
                    Notification.objects.create(
                        recipient=instance.student.user,
                        title='Job Completed',
                        message=completion_message + ' You can now leave a review for your teacher.',
                        notification_type='job_completed',
                        related_object_content_type=ContentType.objects.get_for_model(JobPost),
                        related_object_id=instance.id,
                        action_url=f'/job-board/jobs/{instance.id}/review/',
                    )
                    
                    # Notify teacher
                    Notification.objects.create(
                        recipient=instance.selected_teacher.user,
                        title='Job Completed',
                        message=completion_message + ' You can now leave a review for your student.',
                        notification_type='job_completed',
                        related_object_content_type=ContentType.objects.get_for_model(JobPost),
                        related_object_id=instance.id,
                        action_url=f'/job-board/jobs/{instance.id}/review/',
                    )
                
                elif new_status == 'cancelled':
                    # Notify all applicants about job cancellation
                    for application in instance.applications.filter(status='pending'):
                        Notification.objects.create(
                            recipient=application.teacher.user,
                            title='Job Cancelled',
                            message=f'The job "{instance.title}" has been cancelled by the student.',
                            notification_type='job_cancelled',
                            related_object_content_type=ContentType.objects.get_for_model(JobPost),
                            related_object_id=instance.id,
                            action_url=f'/job-board/jobs/{instance.id}/',
                        )
                        
    except Exception as e:
        print(f"Failed to create job status notification: {e}")


@receiver(post_save, sender=JobReview)
def notify_on_review_received(sender, instance, created, **kwargs):
    """
    Send notification when someone receives a review.
    """
    if not NOTIFICATIONS_AVAILABLE or not created:
        return
    
    try:
        notification_data = {
            'recipient': instance.reviewed,
            'title': 'New Review Received',
            'message': f'You received a {instance.rating}-star review from {instance.reviewer.get_full_name() or instance.reviewer.username} for the job "{instance.job_post.title}".',
            'notification_type': 'review_received',
            'related_object_content_type': ContentType.objects.get_for_model(JobReview),
            'related_object_id': instance.id,
            'action_url': f'/job-board/jobs/{instance.job_post.id}/',
        }
        
        Notification.objects.create(**notification_data)
            
    except Exception as e:
        print(f"Failed to create review notification: {e}")


# Store original status to detect changes
@receiver(post_save, sender=JobApplication)
def store_original_application_status(sender, instance, **kwargs):
    """Store original status to detect changes"""
    try:
        original = JobApplication.objects.get(pk=instance.pk)
        instance._original_status = original.status
    except JobApplication.DoesNotExist:
        instance._original_status = None


@receiver(post_save, sender=JobPost)
def store_original_job_status(sender, instance, **kwargs):
    """Store original status to detect changes"""
    try:
        original = JobPost.objects.get(pk=instance.pk)
        instance._original_status = original.status
    except JobPost.DoesNotExist:
        instance._original_status = None


# Optional: Clean up notifications when jobs/applications are deleted
@receiver(post_delete, sender=JobPost)
def cleanup_job_notifications(sender, instance, **kwargs):
    """Clean up notifications related to deleted jobs"""
    if not NOTIFICATIONS_AVAILABLE:
        return
    
    try:
        # Delete notifications related to this job
        job_content_type = ContentType.objects.get_for_model(JobPost)
        Notification.objects.filter(
            related_object_content_type=job_content_type,
            related_object_id=instance.id
        ).delete()
    except Exception as e:
        print(f"Failed to cleanup job notifications: {e}")


@receiver(post_delete, sender=JobApplication)
def cleanup_application_notifications(sender, instance, **kwargs):
    """Clean up notifications related to deleted applications"""
    if not NOTIFICATIONS_AVAILABLE:
        return
    
    try:
        # Delete notifications related to this application
        app_content_type = ContentType.objects.get_for_model(JobApplication)
        Notification.objects.filter(
            related_object_content_type=app_content_type,
            related_object_id=instance.id
        ).delete()
    except Exception as e:
        print(f"Failed to cleanup application notifications: {e}")