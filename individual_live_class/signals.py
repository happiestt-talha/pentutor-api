# live_classes/signals.py

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from authentication.models import User
from .models import LiveClassSchedule, LiveClassSubscription, LiveClassPayment, LiveClassSession
from .utils import send_schedule_creation_notification, send_payment_confirmation_email
from notifications.models import Notification

@receiver(post_save, sender=LiveClassSchedule)
def schedule_created_handler(sender, instance, created, **kwargs):
    """Handle actions when a new schedule is created"""
    if created:
        try:
            # Send notification emails
            send_schedule_creation_notification(instance)
            
            # Create notification for student - add validation
            if instance.student and instance.student.user:
                Notification.objects.create(
                    recipient=instance.student.user,
                    sender=instance.teacher.user,
                    notification_type='live_class_scheduled',
                    title=f'New Live Class Schedule - {instance.subject}',
                    message=f'{instance.teacher.full_name} has created a live class schedule for {instance.subject}. Your first class will be a FREE demo.'
                )
            else:
                print(f"Warning: Invalid student or user for schedule {instance.id}")
                
        except Exception as e:
            print(f"Error in schedule_created_handler: {e}")
            # Don't raise the exception to prevent transaction rollback

@receiver(post_save, sender=LiveClassSubscription)
def subscription_created_handler(sender, instance, created, **kwargs):
    """Handle actions when a new subscription is created"""
    if created:
        try:
            # Validate relationships before creating notifications
            if (instance.schedule and instance.schedule.teacher and 
                instance.schedule.teacher.user and instance.student and 
                instance.student.user):
                
                # Create notification for teacher
                Notification.objects.create(
                    recipient=instance.schedule.teacher.user,
                    sender=instance.student.user,
                    notification_type='payment_completed',
                    title=f'New Subscription - {instance.schedule.subject}',
                    message=f'{instance.student.full_name} has subscribed to your {instance.schedule.subject} classes ({instance.subscription_type})'
                )
                
                # Create notification for admin - find admin user properly
                admin_users = User.objects.filter(is_staff=True, is_superuser=True)
                if admin_users.exists():
                    admin_user = admin_users.first()
                    Notification.objects.create(
                        recipient=admin_user,
                        sender=instance.student.user,
                        notification_type='payment_completed',
                        title='New Live Class Subscription',
                        message=f'{instance.student.full_name} subscribed to {instance.schedule.subject} - ${instance.amount_paid} ({instance.subscription_type})'
                    )
                else:
                    print("Warning: No admin user found for notification")
            else:
                print(f"Warning: Invalid relationships for subscription {instance.id}")
                
        except Exception as e:
            print(f"Error in subscription_created_handler: {e}")
@receiver(post_save, sender=LiveClassPayment)
def payment_completed_handler(sender, instance, created, **kwargs):
    """Handle actions when payment is completed"""
    if not created and instance.status == 'completed':
        # Send confirmation email
        send_payment_confirmation_email(instance)
        
        # Create notification for student
        Notification.objects.create(
            recipient=instance.student.user,
            notification_type='payment_completed',
            title='Payment Confirmed',
            message=f'Your payment of ${instance.amount} for {instance.schedule.subject} has been confirmed. You can now join your classes.'
        )

@receiver(post_save, sender=LiveClassSession)
def session_created_handler(sender, instance, created, **kwargs):
    """Handle actions when a session is created"""
    if created and instance.is_demo:
        try:
            # Validate relationships
            if (instance.schedule and instance.schedule.student and 
                instance.schedule.student.user and instance.schedule.teacher and 
                instance.schedule.teacher.user):
                
                Notification.objects.create(
                    recipient=instance.schedule.student.user,
                    sender=instance.schedule.teacher.user,
                    notification_type='live_class_scheduled',
                    title=f'Demo Class Scheduled - {instance.schedule.subject}',
                    message=f'Your FREE demo class is scheduled for {instance.scheduled_datetime.strftime("%Y-%m-%d at %H:%M")}. Join through your dashboard.'
                )
            else:
                print(f"Warning: Invalid relationships for session {instance.id}")
                
        except Exception as e:
            print(f"Error in session_created_handler: {e}")


@receiver(pre_save, sender=LiveClassSession)
def session_status_changed_handler(sender, instance, **kwargs):
    """Handle actions when session status changes"""
    if instance.pk:  # Only for existing instances
        try:
            old_instance = LiveClassSession.objects.get(pk=instance.pk)
            
            # Check if status changed to completed
            if old_instance.status != 'completed' and instance.status == 'completed':
                # Create notifications for session completion
                if instance.is_demo:
                    # Demo completed
                    Notification.objects.create(
                        recipient=instance.schedule.student.user,
                        sender=instance.schedule.teacher.user,
                        notification_type='demo_completed',
                        title=f'Demo Class Completed - {instance.schedule.subject}',
                        message=f'Your demo class is complete! To continue with regular classes, please subscribe to the schedule.'
                    )
                    
                    # Notify admin about demo completion
                    Notification.objects.create(
                        recipient_id=1,  # Admin
                        sender=instance.schedule.teacher.user,
                        notification_type='demo_completed',
                        title='Demo Class Completed',
                        message=f'Demo class completed for {instance.schedule.subject} - {instance.schedule.student.full_name} and {instance.schedule.teacher.full_name}'
                    )
                
                else:
                    # Regular class completed
                    Notification.objects.create(
                        recipient=instance.schedule.student.user,
                        sender=instance.schedule.teacher.user,
                        notification_type='general',
                        title=f'Class Completed - {instance.schedule.subject}',
                        message=f'Your class on {instance.scheduled_datetime.strftime("%Y-%m-%d")} has been completed.'
                    )
            
            # Check if session was rescheduled
            if (old_instance.scheduled_datetime != instance.scheduled_datetime and 
                instance.status == 'rescheduled'):
                
                # Notify student
                Notification.objects.create(
                    recipient=instance.schedule.student.user,
                    sender=instance.schedule.teacher.user,
                    notification_type='general',
                    title=f'Class Rescheduled - {instance.schedule.subject}',
                    message=f'Your class has been rescheduled from {old_instance.scheduled_datetime.strftime("%Y-%m-%d %H:%M")} to {instance.scheduled_datetime.strftime("%Y-%m-%d %H:%M")}'
                )
                
                # Notify teacher
                Notification.objects.create(
                    recipient=instance.schedule.teacher.user,
                    notification_type='general',
                    title=f'Class Rescheduled - {instance.schedule.subject}',
                    message=f'Class with {instance.schedule.student.full_name} rescheduled to {instance.scheduled_datetime.strftime("%Y-%m-%d %H:%M")}'
                )
        
        except LiveClassSession.DoesNotExist:
            pass