from django.contrib import admin

# Register your models here.
from .models import Teacher,Course,Video,Question,Quiz,Assignment,Enrollment,Progress

admin.site.register(Teacher)
admin.site.register(Course)
admin.site.register(Video)
admin.site.register(Question)
admin.site.register(Quiz)
admin.site.register(Assignment)
admin.site.register(Enrollment)
admin.site.register(Progress)