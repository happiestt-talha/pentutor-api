# job_board/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import JobPost, JobApplication, JobReview


@admin.register(JobPost)
class JobPostAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'student_name', 'subject_display', 'teaching_mode', 
        'budget_display', 'status', 'applications_count', 'created_at'
    ]
    list_filter = [
        'status', 'teaching_mode', 'budget_type', 'created_at',
        'course', 'duration_unit'
    ]
    search_fields = [
        'title', 'description', 'subject_text', 'student__user__username',
        'student__user__first_name', 'student__user__last_name'
    ]
    readonly_fields = [
        'created_at', 'updated_at', 'applications_count', 'student_profile_link'
    ]
    raw_id_fields = ['student', 'course', 'selected_teacher']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'student', 'student_profile_link')
        }),
        ('Subject & Course', {
            'fields': ('course', 'subject_text'),
            'description': 'Either select a course or provide subject as text'
        }),
        ('Job Details', {
            'fields': (
                'teaching_mode', 'location', 'budget_amount', 'budget_type',
                'duration_value', 'duration_unit', 'deadline'
            )
        }),
        ('Status & Management', {
            'fields': ('status', 'selected_teacher', 'applications_count')
        }),
        ('Additional Information', {
            'fields': ('additional_notes',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def student_name(self, obj):
        return obj.student.user.get_full_name() or obj.student.user.username
    student_name.short_description = 'Student'
    student_name.admin_order_field = 'student__user__username'
    
    def budget_display(self, obj):
        return f"${obj.budget_amount} ({obj.get_budget_type_display()})"
    budget_display.short_description = 'Budget'
    budget_display.admin_order_field = 'budget_amount'
    
    def student_profile_link(self, obj):
        if obj.student:
            url = reverse('admin:authentication_studentprofile_change', args=[obj.student.pk])
            return format_html('<a href="{}" target="_blank">View Student Profile</a>', url)
        return '-'
    student_profile_link.short_description = 'Student Profile'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'student__user', 'course', 'selected_teacher__user'
        ).prefetch_related('applications')


class JobApplicationInline(admin.TabularInline):
    model = JobApplication
    extra = 0
    readonly_fields = ['applied_at', 'updated_at']
    raw_id_fields = ['teacher']
    fields = ['teacher', 'status', 'proposed_rate', 'applied_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('teacher__user')


@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = [
        'job_title', 'teacher_name', 'student_name', 'status', 
        'final_rate', 'applied_at'
    ]
    list_filter = ['status', 'applied_at', 'job_post__status', 'job_post__teaching_mode']
    search_fields = [
        'job_post__title', 'teacher__user__username', 'teacher__user__first_name',
        'teacher__user__last_name', 'job_post__student__user__username'
    ]
    readonly_fields = ['applied_at', 'updated_at', 'final_rate', 'job_link', 'teacher_profile_link']
    raw_id_fields = ['job_post', 'teacher']
    
    fieldsets = (
        ('Application Details', {
            'fields': ('job_post', 'job_link', 'teacher', 'teacher_profile_link', 'status')
        }),
        ('Application Content', {
            'fields': ('cover_letter', 'proposed_rate', 'final_rate')
        }),
        ('Timestamps', {
            'fields': ('applied_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def job_title(self, obj):
        return obj.job_post.title
    job_title.short_description = 'Job'
    job_title.admin_order_field = 'job_post__title'
    
    def teacher_name(self, obj):
        return obj.teacher.user.get_full_name() or obj.teacher.user.username
    teacher_name.short_description = 'Teacher'
    teacher_name.admin_order_field = 'teacher__user__username'
    
    def student_name(self, obj):
        return obj.job_post.student.user.get_full_name() or obj.job_post.student.user.username
    student_name.short_description = 'Student'
    student_name.admin_order_field = 'job_post__student__user__username'
    
    def job_link(self, obj):
        if obj.job_post:
            url = reverse('admin:job_board_jobpost_change', args=[obj.job_post.pk])
            return format_html('<a href="{}" target="_blank">View Job Post</a>', url)
        return '-'
    job_link.short_description = 'Job Post'
    
    def teacher_profile_link(self, obj):
        if obj.teacher:
            url = reverse('admin:authentication_teacherprofile_change', args=[obj.teacher.pk])
            return format_html('<a href="{}" target="_blank">View Teacher Profile</a>', url)
        return '-'
    teacher_profile_link.short_description = 'Teacher Profile'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'job_post__student__user', 'teacher__user'
        )


@admin.register(JobReview)
class JobReviewAdmin(admin.ModelAdmin):
    list_display = [
        'job_title', 'reviewer_name', 'reviewed_name', 'rating', 'created_at'
    ]
    list_filter = ['rating', 'created_at']
    search_fields = [
        'job_post__title', 'reviewer__username', 'reviewed__username',
        'comment'
    ]
    readonly_fields = ['created_at', 'job_link']
    raw_id_fields = ['job_post', 'reviewer', 'reviewed']
    
    fieldsets = (
        ('Review Details', {
            'fields': ('job_post', 'job_link', 'reviewer', 'reviewed', 'rating')
        }),
        ('Review Content', {
            'fields': ('comment',)
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        })
    )
    
    def job_title(self, obj):
        return obj.job_post.title
    job_title.short_description = 'Job'
    job_title.admin_order_field = 'job_post__title'
    
    def reviewer_name(self, obj):
        return obj.reviewer.get_full_name() or obj.reviewer.username
    reviewer_name.short_description = 'Reviewer'
    reviewer_name.admin_order_field = 'reviewer__username'
    
    def reviewed_name(self, obj):
        return obj.reviewed.get_full_name() or obj.reviewed.username
    reviewed_name.short_description = 'Reviewed'
    reviewed_name.admin_order_field = 'reviewed__username'
    
    def job_link(self, obj):
        if obj.job_post:
            url = reverse('admin:job_board_jobpost_change', args=[obj.job_post.pk])
            return format_html('<a href="{}" target="_blank">View Job Post</a>', url)
        return '-'
    job_link.short_description = 'Job Post'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'job_post', 'reviewer', 'reviewed'
        )


# Add inline to JobPost admin
JobPostAdmin.inlines = [JobApplicationInline]


# Custom admin actions
@admin.action(description='Mark selected jobs as completed')
def mark_jobs_completed(modeladmin, request, queryset):
    updated = queryset.update(status='completed')
    modeladmin.message_user(request, f'{updated} jobs marked as completed.')


@admin.action(description='Cancel selected jobs')
def cancel_jobs(modeladmin, request, queryset):
    updated = queryset.update(status='cancelled')
    modeladmin.message_user(request, f'{updated} jobs cancelled.')


@admin.action(description='Accept selected applications')
def accept_applications(modeladmin, request, queryset):
    for application in queryset:
        if application.status == 'pending':
            application.status = 'accepted'
            application.save()
            # Update job post
            job_post = application.job_post
            job_post.status = 'accepted'
            job_post.selected_teacher = application.teacher
            job_post.save()
            # Reject other applications
            JobApplication.objects.filter(
                job_post=job_post
            ).exclude(id=application.id).update(status='rejected')
    
    modeladmin.message_user(request, f'Selected applications processed.')


@admin.action(description='Reject selected applications')
def reject_applications(modeladmin, request, queryset):
    updated = queryset.filter(status='pending').update(status='rejected')
    modeladmin.message_user(request, f'{updated} applications rejected.')


# Add actions to admin classes
JobPostAdmin.actions = [mark_jobs_completed, cancel_jobs]
JobApplicationAdmin.actions = [accept_applications, reject_applications]