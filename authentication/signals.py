# authentication/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User
from .models import TeacherProfile, StudentProfile 

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Automatically create profile for Teacher or Student when a new user is created
    """
    print(f"Signal triggered for user {instance.username} with role {instance.role}")
    if created:
        if instance.role == 'teacher':
            print("Creating TeacherProfile...")
            TeacherProfile.objects.create( user=instance,
                email=instance.email,
                full_name=f"{instance.first_name} {instance.last_name}",  # Or use instance.get_full_name() if using first_name/last_name
                age=instance.age,
                gender=instance.gender,
                city=instance.city,
                country=instance.country)
        elif instance.role == 'student':
            StudentProfile.objects.create(user=instance,
                email=instance.email,
                full_name=f"{instance.first_name} {instance.last_name}",  # Or use instance.get_full_name() if using first_name/last_name
                age=instance.age,
                gender=instance.gender,
                city=instance.city,
                country=instance.country)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    Save the profile when user is saved (if exists)
    """
    if instance.role == 'teacher':
        teacher, created = TeacherProfile.objects.get_or_create(user=instance)
        teacher.save()
    elif instance.role == 'student':
        student, created = StudentProfile.objects.get_or_create(user=instance)
        student.save()
