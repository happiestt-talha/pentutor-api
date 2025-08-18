# notifications/admin.py

from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = [
        'title', 
        'recipient', 
        'sender', 
        'notification_type', 
        'is_read', 
        'created_at'
    ]
    list_filter = [
        'notification_type', 
        'is_read', 
        'created_at',
        'course'
    ]
    search_fields = [
        'title', 
        'message', 
        'recipient__email', 
        'sender__email',
        'course__title'
    ]
    readonly_fields = ['created_at', 'read_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('recipient', 'sender', 'notification_type', 'title', 'message')
        }),
        ('Related Objects', {
            'fields': ('course', 'video', 'quiz', 'meeting'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_read', 'created_at', 'read_at')
        }),
    )
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related(
            'recipient', 'sender', 'course', 'video', 'quiz', 'meeting'
        )
    
    actions = ['mark_as_read', 'mark_as_unread']
    
    def mark_as_read(self, request, queryset):
        updated = 0
        for notification in queryset.filter(is_read=False):
            notification.mark_as_read()
            updated += 1
        
        self.message_user(
            request, 
            f'{updated} notifications were successfully marked as read.'
        )
    mark_as_read.short_description = "Mark selected notifications as read"
    
    def mark_as_unread(self, request, queryset):
        updated = queryset.filter(is_read=True).update(is_read=False, read_at=None)
        self.message_user(
            request, 
            f'{updated} notifications were successfully marked as unread.'
        )
    mark_as_unread.short_description = "Mark selected notifications as unread"