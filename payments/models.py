# payment/models.py - Updated to link with courses

from django.db import models
from django.contrib.auth import get_user_model
from courses.models import Course

User = get_user_model()

class Payment(models.Model):
    GATEWAY_CHOICES = (
        ('jazzcash', 'JazzCash'),
        ('easypaisa', 'EasyPaisa'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='payments',null=True, blank=True)
    gateway = models.CharField(max_length=20, choices=GATEWAY_CHOICES)
    txn_ref = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_successful = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'course']  # Prevent duplicate payments for same course
    
    def __str__(self):
        return f"{self.user.username} - {self.course.title} - {self.gateway} - {self.amount}"
