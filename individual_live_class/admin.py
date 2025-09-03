# live_classes/admin.py

from django.contrib import admin
from .models import (
    LiveClassSchedule, LiveClassSubscription, LiveClassSession,
    ClassReschedule, LiveClassPayment
)


@admin.register(LiveClassSchedule)
class LiveClassScheduleAdmin(admin.ModelAdmin):
    list_display = [
        'schedule_id', 'teacher', 'student', 'subject', 
        'classes_per_week', 'weekly_payment', 'monthly_payment',
        'is_active', 'demo_completed', 'created_at'
    ]
    list_filter = [
        'is_active', 'demo_completed', 'classes_per_week', 'created_at'
    ]
    search_fields = [
        'teacher__full_name', 'student__full_name', 'subject',
        'teacher__user__email', 'student__user__email'
    ]
    readonly_fields = ['schedule_id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('schedule_id', 'teacher', 'student', 'subject')
        }),
        ('Schedule Details', {
            'fields': (
                'classes_per_week', 'class_days', 'class_times', 
                'class_duration', 'start_date', 'end_date'
            )
        }),
        ('Payment Information', {
            'fields': ('weekly_payment', 'monthly_payment')
        }),
        ('Status', {
            'fields': ('is_active', 'demo_completed', 'demo_date')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(LiveClassSubscription)
class LiveClassSubscriptionAdmin(admin.ModelAdmin):
    list_display = [
        'subscription_id', 'student', 'get_schedule_subject', 
        'subscription_type', 'amount_paid', 'classes_included',
        'classes_attended', 'status', 'start_date', 'end_date'
    ]
    list_filter = [
        'subscription_type', 'status', 'start_date', 'created_at'
    ]
    search_fields = [
        'student__full_name', 'student__user__email',
        'schedule__subject', 'transaction_id'
    ]
    readonly_fields = ['subscription_id', 'created_at', 'updated_at', 'payment_date']
    
    def get_schedule_subject(self, obj):
        return obj.schedule.subject
    get_schedule_subject.short_description = 'Subject'


@admin.register(LiveClassSession)
class LiveClassSessionAdmin(admin.ModelAdmin):
    list_display = [
        'session_id', 'get_schedule_subject', 'get_teacher_name',
        'get_student_name', 'scheduled_datetime', 'status',
        'is_demo', 'student_joined', 'teacher_joined'
    ]
    list_filter = [
        'status', 'is_demo', 'student_joined', 'teacher_joined',
        'scheduled_datetime', 'created_at'
    ]
    search_fields = [
        'schedule__subject', 'schedule__teacher__full_name',
        'schedule__student__full_name'
    ]
    readonly_fields = ['session_id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('session_id', 'schedule', 'meeting', 'subscription')
        }),
        ('Session Details', {
            'fields': (
                'scheduled_datetime', 'actual_datetime', 'duration', 
                'status', 'is_demo'
            )
        }),
        ('Attendance Tracking', {
            'fields': (
                'student_joined', 'teacher_joined', 
                'join_time_student', 'join_time_teacher'
            )
        }),
        ('Notes', {
            'fields': ('teacher_notes', 'student_feedback')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_schedule_subject(self, obj):
        return obj.schedule.subject
    get_schedule_subject.short_description = 'Subject'
    
    def get_teacher_name(self, obj):
        return obj.schedule.teacher.full_name
    get_teacher_name.short_description = 'Teacher'
    
    def get_student_name(self, obj):
        return obj.schedule.student.full_name
    get_student_name.short_description = 'Student'


@admin.register(ClassReschedule)
class ClassRescheduleAdmin(admin.ModelAdmin):
    list_display = [
        'get_session_subject', 'get_teacher_name', 'get_student_name',
        'original_datetime', 'new_datetime', 'requested_by',
        'is_approved', 'created_at'
    ]
    list_filter = [
        'is_approved', 'created_at', 'approved_at'
    ]
    search_fields = [
        'session__schedule__subject', 'session__schedule__teacher__full_name',
        'session__schedule__student__full_name', 'requested_by__username'
    ]
    readonly_fields = ['created_at', 'approved_at']
    
    fieldsets = (
        ('Session Information', {
            'fields': ('session',)
        }),
        ('Reschedule Details', {
            'fields': ('original_datetime', 'new_datetime', 'reason')
        }),
        ('Request Information', {
            'fields': ('requested_by', 'approved_by', 'is_approved')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'approved_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_session_subject(self, obj):
        return obj.session.schedule.subject
    get_session_subject.short_description = 'Subject'
    
    def get_teacher_name(self, obj):
        return obj.session.schedule.teacher.full_name
    get_teacher_name.short_description = 'Teacher'
    
    def get_student_name(self, obj):
        return obj.session.schedule.student.full_name
    get_student_name.short_description = 'Student'


@admin.register(LiveClassPayment)
class LiveClassPaymentAdmin(admin.ModelAdmin):
    list_display = [
        'payment_id', 'student', 'get_schedule_subject', 
        'amount', 'payment_method', 'status', 
        'transaction_reference', 'initiated_at'
    ]
    list_filter = [
        'status', 'payment_method', 'initiated_at', 'completed_at'
    ]
    search_fields = [
        'student__full_name', 'student__user__email',
        'schedule__subject', 'transaction_reference'
    ]
    readonly_fields = [
        'payment_id', 'initiated_at', 'completed_at'
    ]
    
    fieldsets = (
        ('Payment Information', {
            'fields': (
                'payment_id', 'subscription', 'student', 'schedule'
            )
        }),
        ('Transaction Details', {
            'fields': (
                'amount', 'payment_method', 'transaction_reference', 'status'
            )
        }),
        ('Gateway Response', {
            'fields': ('gateway_response', 'failure_reason'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('initiated_at', 'completed_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_schedule_subject(self, obj):
        return obj.schedule.subject
    get_schedule_subject.short_description = 'Subject'