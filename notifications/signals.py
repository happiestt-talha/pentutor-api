# notifications/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from courses.models import Video, Quiz, Enrollment
from meetings.models import Meeting
from payments.models import Payment
from .models import Notification
from authentication.models import TeacherProfile,StudentProfile,StudentQuery

User = get_user_model()


@receiver(post_save, sender=Video)
def notify_video_upload(sender, instance, created, **kwargs):
    """
    Send notification to all enrolled students when a new video is uploaded
    """
    if created:  # Only for new videos
        # Get all enrolled students in the course
        enrolled_students = instance.course.enrollments.filter(
           payment_status='verified',
            student__isnull=False
        ).select_related('student')
        
        # Create notifications for each enrolled student
        notifications_to_create = []
        for enrollment in enrolled_students:
            notification = Notification(
                recipient=enrollment.student,
                sender=instance.course.teacher.user,
                notification_type='video_upload',
                title=f'New Video: {instance.title}',
                message=f'A new video "{instance.title}" has been uploaded to the course "{instance.course.title}". Check it out now!',
                course=instance.course,
                video=instance
            )
            notifications_to_create.append(notification)
        
        # Bulk create notifications for better performance
        if notifications_to_create:
            Notification.objects.bulk_create(notifications_to_create)


@receiver(post_save, sender=Quiz)
def notify_quiz_creation(sender, instance, created, **kwargs):
    """
    Send notification to all enrolled students when a new quiz is created
    """
    if created:  # Only for new quizzes
        # Get all enrolled students in the course
        enrolled_students = instance.course.enrollments.filter(
            payment_status='verified',
            student__isnull=False
        ).select_related('student')
        
        # Create notifications for each enrolled student
        notifications_to_create = []
        for enrollment in enrolled_students:
            notification = Notification(
                recipient=enrollment.student,
                sender=instance.course.teacher.user,
                notification_type='quiz_created',
                title=f'New Quiz: {instance.title}',
                message=f'A new quiz "{instance.title}" has been created for the course "{instance.course.title}". Test your knowledge!',
                course=instance.course,
                quiz=instance
            )
            notifications_to_create.append(notification)
        
        # Bulk create notifications for better performance
        if notifications_to_create:
            Notification.objects.bulk_create(notifications_to_create)


@receiver(post_save, sender=Payment)
def notify_payment_completion(sender, instance, created, **kwargs):
    """
    Send notification to admin and teacher when a student completes payment and enrolls
    """
    if instance.is_successful and instance.course:
        # Check if enrollment exists (payment successful means student is enrolled)
        try:
            enrollment = Enrollment.objects.get(
                student=instance.user,
                course=instance.course
            )
            
            # Get admin users and the course teacher
            admin_users = User.objects.filter(role__in=['admin', 'subadmin'])
            teacher = instance.course.teacher.user
            
            # Create notifications for admins
            notifications_to_create = []
            for admin in admin_users:
                notification = Notification(
                    recipient=admin,
                    sender=instance.user,
                    notification_type='student_enrolled',
                    title=f'New Enrollment: {instance.user.get_full_name() or instance.user.username}',
                    message=f'{instance.user.get_full_name() or instance.user.username} has successfully enrolled in "{instance.course.title}" after completing payment of ${instance.amount}.',
                    course=instance.course
                )
                notifications_to_create.append(notification)
            
            # Create notification for teacher (if teacher is not already in admin list)
            if teacher not in admin_users:
                notification = Notification(
                    recipient=teacher,
                    sender=instance.user,
                    notification_type='student_enrolled',
                    title=f'New Student: {instance.user.get_full_name() or instance.user.username}',
                    message=f'{instance.user.get_full_name() or instance.user.username} has enrolled in your course "{instance.course.title}" after completing payment.',
                    course=instance.course
                )
                notifications_to_create.append(notification)
            
            # Bulk create notifications
            if notifications_to_create:
                Notification.objects.bulk_create(notifications_to_create)
                
        except Enrollment.DoesNotExist:
            pass  # No enrollment found, skip notification


@receiver(post_save, sender=Meeting)
def notify_live_class_scheduled(sender, instance, created, **kwargs):
    """
    Send notification to all enrolled students when a live class is scheduled
    """
    if created and instance.meeting_type == 'lecture' and instance.course and instance.scheduled_time:
        # Get all enrolled students in the course
        enrolled_students = instance.course.enrollments.filter(
            payment_status='verified',
            student__isnull=False
        ).select_related('student')
        
        # Format the scheduled time
        scheduled_time_str = instance.scheduled_time.strftime('%B %d, %Y at %I:%M %p')
        
        # Create notifications for each enrolled student
        notifications_to_create = []
        for enrollment in enrolled_students:
            notification = Notification(
                recipient=enrollment.student,
                sender=instance.host,
                notification_type='live_class_scheduled',
                title=f'Live Class Scheduled: {instance.title}',
                message=f'A live class "{instance.title}" has been scheduled for "{instance.course.title}" on {scheduled_time_str}. Don\'t miss it!',
                course=instance.course,
                meeting=instance
            )
            notifications_to_create.append(notification)
        
        # Bulk create notifications for better performance
        if notifications_to_create:
            Notification.objects.bulk_create(notifications_to_create)


# Alternative signal for enrollment (if you want to notify on enrollment directly)
@receiver(post_save, sender=Enrollment)
def notify_enrollment_direct(sender, instance, created, **kwargs):
    """
    Alternative notification for direct enrollment (for free courses)
    This will only trigger if the enrollment is for a free course
    """
    if created and instance.course.course_type == 'free':
        # Get admin users and the course teacher
        admin_users = User.objects.filter(role__in=['admin', 'subadmin'])
        teacher = instance.course.teacher.user

        student_name = (
            instance.student.full_name or
            instance.student.user.get_full_name() or
            instance.student.user.username
        )
        
        # Create notifications for admins
        notifications_to_create = []
        for admin in admin_users:
            notification = Notification(
                recipient=admin,
                sender=instance.student.user,
                notification_type='student_enrolled',
                title=f'New Free Enrollment: {student_name}',
                message=f'{student_name} has enrolled in the free course "{instance.course.title}".',
                course=instance.course
            )
            notifications_to_create.append(notification)
        
        # Create notification for teacher (if teacher is not already in admin list)
        if teacher not in admin_users:
            notification = Notification(
                recipient=teacher,
                sender=instance.student.user,
                notification_type='student_enrolled',
                title=f'New Student: {student_name}',
                message=f'{student_name} has enrolled in your free course "{instance.course.title}".',
                course=instance.course
            )
            notifications_to_create.append(notification)
        
        # Bulk create notifications
        if notifications_to_create:
            Notification.objects.bulk_create(notifications_to_create)



def send_admin_notification(sender,instance, role_type):
    """Send notification + email to all admins"""
    admins = User.objects.filter(is_superuser=True)
    sender_user = getattr(instance, "user", None) or getattr(instance, "linked_user", None)

    # Message build karo
    if isinstance(instance, StudentQuery):
        title = f"New Student Query"
        message = f"A new student query has been submitted by {instance.name} ({instance.email}) from {instance.area}. Subject interests: {instance.subjects}"
    else:
        title = f"New {role_type.replace('_', ' ').title()}"
        message = f"{sender_user.username if sender_user else 'Unknown'} has requested to become a {role_type.split('_')[0]}."

    for admin in admins:
        Notification.objects.create(
            recipient=admin,
            sender=sender_user,  # ho to user, warna None
            notification_type=role_type,
            title=title,
            message=message
        )

@receiver(post_save, sender=StudentProfile)
def student_role_request_created(sender, instance, created, **kwargs):
    if created:
        send_admin_notification(sender, instance, "student_request")


@receiver(post_save, sender=TeacherProfile)
def teacher_role_request_created(sender, instance, created, **kwargs):
    if created:
        send_admin_notification(sender, instance, "teacher_request")

@receiver(post_save,sender=StudentQuery)
def student_query_form_created(sender, instance, created, **kwargs):
    if created:
        send_admin_notification(sender,instance, "student_query")
