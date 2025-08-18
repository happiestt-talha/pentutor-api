from django.contrib import admin
from .models import Meeting,Participant
# Register your models here.

admin.site.register(Meeting)
admin.site.register(Participant)

# admin.site.register(JoinRequest)
