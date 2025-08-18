from django.contrib import admin
from .models import CourseFeedback,TeacherFeedback,TicketReply,SupportTicket
# Register your models here.

admin.site.register(CourseFeedback)
admin.site.register(TeacherFeedback)
admin.site.register(TicketReply)
admin.site.register(SupportTicket)