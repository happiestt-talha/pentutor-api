from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import (
    EmailTemplate,
    EmailLog,
    EmailPreference,
    WeeklyProgressReport,
    EmailQueue
)


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'email_type', 'is_active', 'created_at', 'updated_at']
    list_filter = ['email_type', 'is_active', 'created_at']
    search_fields = ['name', 'subject']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'email_type', 'is_active')
        }),
        ('Email Content', {
            'fields': ('subject', 'html_content', 'text_content')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return self.readonly_fields + ('email_type',)
        return self.readonly_fields


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = [
        'recipient_email', 'email_type', 'subject_truncated', 
        'status', 'sent_at', 'created_at'
    ]
    list_filter = ['email_type', 'status', 'sent_at', 'created_at']
    search_fields = ['recipient__email', 'subject']
    readonly_fields = [
        'recipient', 'email_type', 'subject', 'content', 'status',
        'sent_at', 'delivered_at', 'opened_at', 'clicked_at',
        'error_message', 'course', 'enrollment', 'payment',
        'created_at', 'updated_at'
    ]
    
    def recipient_email(self, obj):
        return obj.recipient.email
    recipient_email.short_description = 'Recipient'
    
    def subject_truncated(self, obj):
        return obj.subject[:50] + '...' if len(obj.subject) > 50 else obj.subject
    subject_truncated.short_description = 'Subject'
    
    def has_add_permission(self, request):
        return False  # Don't allow manual creation of email logs
    
    def has_change_permission(self, request, obj=None):
        return False  # Don't allow editing of email logs
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser  # Only superusers can delete logs


@admin.register(EmailPreference)
class EmailPreferenceAdmin(admin.ModelAdmin):
    list_display = [
        'user_email', 'is_subscribed', 'enrollment_emails', 
        'demo_emails', 'payment_emails', 'progress_emails', 
        'content_emails', 'updated_at'
    ]
    list_filter = [
        'is_subscribed', 'enrollment_emails', 'demo_emails',
        'payment_emails', 'progress_emails', 'content_emails'
    ]
    search_fields = ['user__email', 'user__username']
    readonly_fields = ['created_at', 'updated_at']
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User Email'
    
    fieldsets = (
        (None, {
            'fields': ('user', 'is_subscribed', 'unsubscribed_at')
        }),
        ('Email Type Preferences', {
            'fields': (
                'enrollment_emails', 'demo_emails', 'payment_emails',
                'progress_emails', 'content_emails'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(WeeklyProgressReport)
class WeeklyProgressReportAdmin(admin.ModelAdmin):
    list_display = [
        'user_email', 'course_title', 'week_start', 'week_end',
        'completion_percentage', 'report_generated', 'email_sent', 'created_at'
    ]
    list_filter = [
        'week_start', 'report_generated', 'email_sent', 'created_at'
    ]
    search_fields = ['user__email', 'course__title']
    readonly_fields = [
        'user', 'course', 'week_start', 'week_end',
        'videos_completed', 'total_videos', 'quizzes_completed',
        'total_quizzes', 'assignments_completed', 'total_assignments',
        'time_spent', 'completion_percentage', 'created_at'
    ]
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User'
    
    def course_title(self, obj):
        return obj.course.title
    course_title.short_description = 'Course'
    
    fieldsets = (
        (None, {
            'fields': ('user', 'course', 'week_start', 'week_end')
        }),
        ('Progress Metrics', {
            'fields': (
                ('videos_completed', 'total_videos'),
                ('quizzes_completed', 'total_quizzes'),
                ('assignments_completed', 'total_assignments'),
                'time_spent', 'completion_percentage'
            )
        }),
        ('Status', {
            'fields': ('report_generated', 'email_sent')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(EmailQueue)
class EmailQueueAdmin(admin.ModelAdmin):
    list_display = [
        'recipient_email', 'email_type', 'subject_truncated',
        'priority', 'scheduled_at', 'is_processed', 'retry_count'
    ]
    list_filter = [
        'email_type', 'priority', 'is_processed', 'scheduled_at'
    ]
    search_fields = ['recipient__email', 'subject']
    readonly_fields = [
        'recipient', 'email_type', 'subject', 'content',
        'context_data', 'created_at'
    ]
    
    def recipient_email(self, obj):
        return obj.recipient.email
    recipient_email.short_description = 'Recipient'
    
    def subject_truncated(self, obj):
        return obj.subject[:50] + '...' if len(obj.subject) > 50 else obj.subject
    subject_truncated.short_description = 'Subject'
    
    fieldsets = (
        (None, {
            'fields': ('recipient', 'email_type', 'subject', 'priority')
        }),
        ('Content', {
            'fields': ('content', 'context_data'),
            'classes': ('collapse',)
        }),
        ('Scheduling', {
            'fields': ('scheduled_at', 'max_retries', 'retry_count')
        }),
        ('Status', {
            'fields': ('is_processed', 'processed_at')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_processed', 'reset_retry_count']
    
    def mark_as_processed(self, request, queryset):
        updated = queryset.update(is_processed=True)
        self.message_user(request, f'{updated} emails marked as processed.')
    mark_as_processed.short_description = 'Mark selected emails as processed'
    
    def reset_retry_count(self, request, queryset):
        updated = queryset.update(retry_count=0)
        self.message_user(request, f'Retry count reset for {updated} emails.')
    reset_retry_count.short_description = 'Reset retry count for selected emails'
