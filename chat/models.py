from django.db import models
# Create your models here.


# Create your models here.
class ChatMessage(models.Model):
    room_id = models.CharField(max_length=255)
    user = models.CharField(max_length=255)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def _str_(self):
        return f"{self.room_id} | {self.user}: {self.message}"