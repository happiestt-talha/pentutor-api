# live_classes/serializers.py

from rest_framework import serializers
from .models import (
    LiveClassSchedule, LiveClassSubscription, LiveClassSession, 
    ClassReschedule, LiveClassPayment
)
from authentication.models import StudentProfile, TeacherProfile
from meetings.models import Meeting
import uuid


class LiveClassScheduleSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source='teacher.full_name', read_only=True)
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    next_class_date = serializers.SerializerMethodField()
    
    class Meta:
        model = LiveClassSchedule
        fields = '__all__'
        read_only_fields = ('schedule_id', 'created_at', 'updated_at', 'demo_completed', 'demo_date')
    
    def get_next_class_date(self, obj):
        next_date = obj.get_next_class_date()
        return next_date.isoformat() if next_date else None

class LiveClassScheduleCreateSerializer(serializers.ModelSerializer):
    # frontend se sirf ek identifier aayega (uuid/email/username)
    # student_identifier = serializers.CharField(write_only=True)

    class Meta:
        model = LiveClassSchedule
        fields = [
            'student', 'subject', 'classes_per_week', 'class_days',
            'class_times', 'class_duration', 'weekly_payment',
            'monthly_payment', 'start_date', 'end_date'
        ]

    # def create(self, validated_data):
    #     identifier = validated_data.pop("student_identifier")

    #     # Try UUID first
    #     student_obj = None
    #     try:
    #         student_obj = StudentProfile.objects.get(id=identifier)
    #     except (ValueError, StudentProfile.DoesNotExist):
    #         # Try email
    #         try:
    #             student_obj = StudentProfile.objects.get(user__email=identifier)
    #         except StudentProfile.DoesNotExist:
    #             # Try username
    #             try:
    #                 student_obj = StudentProfile.objects.get(user__username=identifier)
    #             except StudentProfile.DoesNotExist:
    #                 raise serializers.ValidationError(
    #                     {"student_identifier": "No student found with given identifier"}
    #                 )

    #     validated_data["student"] = student_obj
    #     return super().create(validated_data)

    def validate_class_days(self, value):
        valid_days = ['monday', 'tuesday', 'wednesday', 'thursday',
                      'friday', 'saturday', 'sunday']
        if not all(day in valid_days for day in value):
            raise serializers.ValidationError("Invalid day provided")
        return value

    def validate(self, data):
        if len(data['class_days']) != data['classes_per_week']:
            raise serializers.ValidationError(
                "Number of class days must match classes per week"
            )
        if len(data['class_times']) != data['classes_per_week']:
            raise serializers.ValidationError(
                "Number of class times must match classes per week"
            )
        return data

class LiveClassSubscriptionSerializer(serializers.ModelSerializer):
    schedule_subject = serializers.CharField(source='schedule.subject', read_only=True)
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    is_valid = serializers.SerializerMethodField()
    can_attend = serializers.SerializerMethodField()
    
    class Meta:
        model = LiveClassSubscription
        fields = '__all__'
        read_only_fields = ('subscription_id', 'created_at', 'updated_at', 'payment_date')
    
    def get_is_valid(self, obj):
        return obj.is_valid()
    
    def get_can_attend(self, obj):
        return obj.can_attend_class()


class LiveClassSessionSerializer(serializers.ModelSerializer):
    schedule_subject = serializers.CharField(source='schedule.subject', read_only=True)
    teacher_name = serializers.CharField(source='schedule.teacher.full_name', read_only=True)
    student_name = serializers.CharField(source='schedule.student.full_name', read_only=True)
    meeting_id = serializers.CharField(source='meeting.meeting_id', read_only=True)
    
    class Meta:
        model = LiveClassSession
        fields = '__all__'
        read_only_fields = ('session_id', 'created_at', 'updated_at')


class ClassRescheduleSerializer(serializers.ModelSerializer):
    session_subject = serializers.CharField(source='session.schedule.subject', read_only=True)
    requested_by_name = serializers.CharField(source='requested_by.username', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.username', read_only=True)
    
    class Meta:
        model = ClassReschedule
        fields = '__all__'
        read_only_fields = ('created_at', 'approved_at')


class RescheduleRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClassReschedule
        fields = ['session', 'new_datetime', 'reason']


class LiveClassPaymentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    schedule_subject = serializers.CharField(source='schedule.subject', read_only=True)
    
    class Meta:
        model = LiveClassPayment
        fields = '__all__'
        read_only_fields = ('payment_id', 'initiated_at', 'completed_at')


class SubscriptionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LiveClassSubscription
        fields = [
            'schedule', 'subscription_type', 'amount_paid', 
            'classes_included', 'start_date', 'end_date', 
            'payment_method', 'transaction_id'
        ]


class TeacherScheduleListSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    student_email = serializers.CharField(source='student.user.email', read_only=True)
    student_profile_picture = serializers.SerializerMethodField()
    active_subscription = serializers.SerializerMethodField()
    next_class = serializers.SerializerMethodField()
    
    class Meta:
        model = LiveClassSchedule
        fields = [
            'schedule_id', 'student_name', 'student_email','student_profile_picture', 'subject',
            'classes_per_week', 'class_days', 'class_times', 'class_duration',
            'weekly_payment', 'monthly_payment', 'is_active', 'demo_completed',
            'active_subscription', 'next_class', 'created_at'
        ]
    
    def get_active_subscription(self, obj):
        active_sub = obj.subscriptions.filter(status='active').first()
        return LiveClassSubscriptionSerializer(active_sub).data if active_sub else None
    
    def get_student_profile_picture(self, obj):
        """Get student's profile picture URL"""
        if obj.student.profile_picture:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.student.profile_picture.url)
            return obj.student.profile_picture.url
        return None

    
    def get_next_class(self, obj):
        next_date = obj.get_next_class_date()
        return next_date.isoformat() if next_date else None
    

class StudentScheduleListSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source='teacher.full_name', read_only=True)
    teacher_email = serializers.CharField(source='teacher.user.email', read_only=True)
    active_subscription = serializers.SerializerMethodField()
    next_class = serializers.SerializerMethodField()
    can_join = serializers.SerializerMethodField()
    
    class Meta:
        model = LiveClassSchedule
        fields = [
            'schedule_id', 'teacher_name', 'teacher_email', 'subject',
            'classes_per_week', 'class_days', 'class_times', 'class_duration',
            'weekly_payment', 'monthly_payment', 'demo_completed',
            'active_subscription', 'next_class', 'can_join', 'created_at'
        ]
    
    def get_active_subscription(self, obj):
        active_sub = obj.subscriptions.filter(
            student=obj.student, 
            status='active'
        ).first()
        return LiveClassSubscriptionSerializer(active_sub).data if active_sub else None
    
    def get_next_class(self, obj):
        next_date = obj.get_next_class_date()
        return next_date.isoformat() if next_date else None
    
    def get_can_join(self, obj):
        # Can join if demo not completed or has active subscription
        if not obj.demo_completed:
            return True
        
        active_sub = obj.subscriptions.filter(
            student=obj.student,
            status='active'
        ).first()
        
        return active_sub.can_attend_class() if active_sub else False
    

class MeetingRescheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Meeting
        fields = ['id', 'scheduled_time']   # sirf ye update karna allow
        read_only_fields = ['id']