# live_classes/views.py

from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from datetime import datetime, timedelta
from rest_framework.exceptions import ValidationError

from .models import (
    LiveClassSchedule, LiveClassSubscription, LiveClassSession,
    ClassReschedule, LiveClassPayment
)
import uuid
from .serializers import (
    LiveClassScheduleSerializer, LiveClassScheduleCreateSerializer,
    LiveClassSubscriptionSerializer, LiveClassSessionSerializer,
    ClassRescheduleSerializer, RescheduleRequestSerializer,
    LiveClassPaymentSerializer, SubscriptionCreateSerializer,
    TeacherScheduleListSerializer, StudentScheduleListSerializer,MeetingRescheduleSerializer
)
from authentication.models import StudentProfile, TeacherProfile,User
from meetings.models import Meeting
from notifications.models import Notification


# Teacher Views
class TeacherScheduleListView(generics.ListAPIView):
    """List all schedules created by a teacher"""
    serializer_class = TeacherScheduleListSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        teacher_profile = get_object_or_404(TeacherProfile, user=self.request.user)
        return LiveClassSchedule.objects.filter(teacher=teacher_profile)
    def get_serializer_context(self):
        """Pass request to serializer for building absolute URLs"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class CreateLiveClassScheduleView(generics.CreateAPIView):
    """Teacher creates a live class schedule for a student"""
    serializer_class = LiveClassScheduleCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    try:
        def perform_create(self, serializer):
            teacher_profile = get_object_or_404(TeacherProfile, user=self.request.user)
            # Check if schedule already exists
            print("Student:", serializer.validated_data.get("student"))
            # Convert student UUID string to UUID object for filtering
            student_obj = serializer.validated_data["student"]
            print("studnet obj: ",student_obj)
            # Validate student exists and has user relationship
            if not student_obj or not hasattr(student_obj, 'user'):
                raise ValidationError({"student": "Invalid student profile"})
            
            try:
                existing_schedule = LiveClassSchedule.objects.filter(
                    teacher=teacher_profile,
                    student=student_obj,
                    subject=serializer.validated_data['subject']
                ).first()
                print("exsiting schedule: ",existing_schedule)
            

                if existing_schedule:
                    raise ValidationError(
                        {"detail": "A schedule already exists for this teacher, student, and subject."}
                    )
            except Exception as e:
                print("Ecept error",e)
                raise
        
            # try:
            #     student_obj = StudentProfile.objects.get(id=student_uuid)
            # except StudentProfile.DoesNotExist:
            #     raise ValidationError({"student": "Student not found"})
            schedule = serializer.save(teacher=teacher_profile)
            print("save")
            
            # Create demo meeting
            demo_meeting = schedule.create_demo_class()
            if demo_meeting:
                # Create demo session
                LiveClassSession.objects.create(
                    schedule=schedule,
                    meeting=demo_meeting,
                    scheduled_datetime=demo_meeting.scheduled_time,
                    duration=schedule.class_duration,
                    is_demo=True
                )
            
            # admin_user = User.objects.filter(role__in="admin").first()
            # print("Admin user:", admin_user)
            # print("Sender:", self.request.user)
            # if admin_user:
            #         Notification.objects.create(
            #             recipient=admin_user,   # pass object, not raw id
            #             sender=self.request.user,
            #             notification_type='general',
            #             title='New Live Class Schedule Created',
            #             message=f'{teacher_profile.full_name} created a schedule for {schedule.subject} with {schedule.student.full_name}'
            #         )
            # else:
            #     print("⚠️ No admin user found, skipping notification")
    except Exception as e:
        print(f"Error creating Sheduale : {e}")
        raise

class UpdateLiveClassScheduleView(generics.UpdateAPIView):
    """Teacher updates their live class schedule"""
    serializer_class = LiveClassScheduleSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'schedule_id'
    
    def get_queryset(self):
        teacher_profile = get_object_or_404(TeacherProfile, user=self.request.user)
        return LiveClassSchedule.objects.filter(teacher=teacher_profile)

class RescheduleMeetingView(generics.UpdateAPIView):
    """Teacher updates (reschedules) a single meeting"""
    serializer_class = MeetingRescheduleSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'   # Meeting ka id use karenge

    def get_queryset(self):
        # Sirf apne meetings update kar sake
        return Meeting.objects.filter(host=self.request.user)
# Student Views
class StudentScheduleListView(generics.ListAPIView):
    """List all schedules for a student"""
    serializer_class = StudentScheduleListSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        student_profile = get_object_or_404(StudentProfile, user=self.request.user)
        return LiveClassSchedule.objects.filter(student=student_profile)


class StudentSubscriptionListView(generics.ListAPIView):
    """List student's subscriptions"""
    serializer_class = LiveClassSubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        student_profile = get_object_or_404(StudentProfile, user=self.request.user)
        return LiveClassSubscription.objects.filter(student=student_profile)


class CreateSubscriptionView(generics.CreateAPIView):
    """Student creates a subscription for live classes"""
    serializer_class = SubscriptionCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        student_profile = get_object_or_404(StudentProfile, user=self.request.user)
        subscription = serializer.save(student=student_profile)
        
        # Create payment record
        payment = LiveClassPayment.objects.create(
            subscription=subscription,
            student=student_profile,
            schedule=subscription.schedule,
            amount=subscription.amount_paid,
            payment_method=subscription.payment_method,
            transaction_reference=subscription.transaction_id,
            status='completed'
        )
        payment.mark_completed()


# Session Management Views
class SessionListView(generics.ListAPIView):
    """List sessions - filtered by user role"""
    serializer_class = LiveClassSessionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        if hasattr(user, 'teacher_profile'):
            return LiveClassSession.objects.filter(
                schedule__teacher=user.teacher_profile
            ).order_by('-scheduled_datetime')
        elif hasattr(user, 'student_profile'):
            return LiveClassSession.objects.filter(
                schedule__student=user.student_profile
            ).order_by('-scheduled_datetime')
        else:
            return LiveClassSession.objects.none()


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def join_live_class(request, schedule_id):
    """Student or teacher joins a live class"""
    schedule = get_object_or_404(LiveClassSchedule, schedule_id=schedule_id)
    user = request.user
    
    # Check if user can join
    if hasattr(user, 'student_profile'):
        student = user.student_profile
        if schedule.student != student:
            return Response(
                {'error': 'You are not enrolled in this schedule'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if demo or has active subscription
        if not schedule.demo_completed:
            can_join = True
        else:
            active_sub = LiveClassSubscription.objects.filter(
                schedule=schedule,
                student=student,
                status='active'
            ).first()
            can_join = active_sub and active_sub.can_attend_class()
        
        if not can_join:
            return Response(
                {'error': 'No active subscription or demo completed'}, 
                status=status.HTTP_403_FORBIDDEN
            )
    
    elif hasattr(user, 'teacher_profile'):
        if schedule.teacher != user.teacher_profile:
            return Response(
                {'error': 'You are not the teacher for this schedule'}, 
                status=status.HTTP_403_FORBIDDEN
            )
    else:
        return Response(
            {'error': 'Invalid user type'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Get or create current session
    now = timezone.now()
    current_session = LiveClassSession.objects.filter(
        schedule=schedule,
        scheduled_datetime__date=now.date(),
        status__in=['scheduled', 'ongoing']
    ).first()
    
    if not current_session:
        return Response(
            {'error': 'No scheduled class found for today'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Create or get meeting
    meeting = current_session.meeting
    if not meeting:
        meeting = current_session.create_meeting()
    
    # Update session status
    if current_session.status == 'scheduled':
        current_session.status = 'ongoing'
        current_session.actual_datetime = now
        current_session.save()
    
    # Track join time
    if hasattr(user, 'student_profile'):
        current_session.student_joined = True
        current_session.join_time_student = now
    elif hasattr(user, 'teacher_profile'):
        current_session.teacher_joined = True
        current_session.join_time_teacher = now
    
    current_session.save()
    
    return Response({
        'meeting_id': meeting.meeting_id,
        'meeting_password': meeting.password,
        'session_id': current_session.session_id
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def end_live_class(request, session_id):
    """Teacher ends a live class session"""
    session = get_object_or_404(LiveClassSession, session_id=session_id)
    
    # Only teacher can end class
    if not hasattr(request.user, 'teacher_profile') or session.schedule.teacher != request.user.teacher_profile:
        return Response(
            {'error': 'Only the teacher can end the class'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Mark session as completed
    session.mark_completed()
    
    # End meeting if exists
    if session.meeting:
        session.meeting.end_meeting()
    
    # Mark demo as completed if it was a demo
    if session.is_demo:
        session.schedule.demo_completed = True
        session.schedule.demo_date = timezone.now()
        session.schedule.save()
    
    return Response({'message': 'Class ended successfully'})


# Reschedule Views
class RescheduleRequestView(generics.CreateAPIView):
    """Create a reschedule request"""
    serializer_class = RescheduleRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        serializer.save(requested_by=self.request.user)
        
        # Notify admin
        reschedule = serializer.instance
        Notification.objects.create(
            recipient_id=1,  # Admin
            sender=self.request.user,
            notification_type='general',
            title='Class Reschedule Request',
            message=f'Reschedule requested for {reschedule.session.schedule.subject} from {reschedule.original_datetime} to {reschedule.new_datetime}'
        )


class PendingReschedulesView(generics.ListAPIView):
    """List pending reschedule requests for admin"""
    serializer_class = ClassRescheduleSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # Only admin can view
        if self.request.user.role != 'admin':
            return ClassReschedule.objects.none()
        return ClassReschedule.objects.filter(is_approved=False)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def approve_reschedule(request, reschedule_id):
    """Admin approves a reschedule request"""
    if request.user.role != 'admin':
        return Response(
            {'error': 'Only admin can approve reschedules'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    reschedule = get_object_or_404(ClassReschedule, id=reschedule_id)
    reschedule.approve_reschedule(request.user)
    
    return Response({'message': 'Reschedule approved successfully'})


# Admin Views
class AdminScheduleListView(generics.ListAPIView):
    """Admin view of all schedules"""
    serializer_class = LiveClassScheduleSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.role != 'admin':
            return LiveClassSchedule.objects.none()
        return LiveClassSchedule.objects.all().order_by('-created_at')


class AdminPaymentListView(generics.ListAPIView):
    """Admin view of all payments"""
    serializer_class = LiveClassPaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.role != 'admin':
            return LiveClassPayment.objects.none()
        return LiveClassPayment.objects.all().order_by('-initiated_at')


class AdminSessionListView(generics.ListAPIView):
    """Admin view of all sessions"""
    serializer_class = LiveClassSessionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.role != 'admin':
            return LiveClassSession.objects.none()
        return LiveClassSession.objects.all().order_by('-scheduled_datetime')


# Utility Views
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def schedule_analytics(request, schedule_id):
    """Get analytics for a specific schedule"""
    schedule = get_object_or_404(LiveClassSchedule, schedule_id=schedule_id)
    
    # Check permissions
    user = request.user
    if hasattr(user, 'teacher_profile'):
        if schedule.teacher != user.teacher_profile:
            return Response(
                {'error': 'Access denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
    elif hasattr(user, 'student_profile'):
        if schedule.student != user.student_profile:
            return Response(
                {'error': 'Access denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
    elif user.role != 'admin':
        return Response(
            {'error': 'Access denied'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Calculate analytics
    sessions = schedule.sessions.all()
    total_sessions = sessions.count()
    completed_sessions = sessions.filter(status='completed').count()
    missed_sessions = sessions.filter(status='missed').count()
    
    active_subscription = schedule.subscriptions.filter(status='active').first()
    
    analytics = {
        'total_sessions': total_sessions,
        'completed_sessions': completed_sessions,
        'missed_sessions': missed_sessions,
        'attendance_rate': (completed_sessions / total_sessions * 100) if total_sessions > 0 else 0,
        'demo_completed': schedule.demo_completed,
        'active_subscription': LiveClassSubscriptionSerializer(active_subscription).data if active_subscription else None,
        'total_subscriptions': schedule.subscriptions.count(),
        'total_revenue': sum(sub.amount_paid for sub in schedule.subscriptions.filter(status__in=['active', 'expired']))
    }
    
    return Response(analytics)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def upcoming_classes(request):
    """Get upcoming classes for user"""
    user = request.user
    
    if hasattr(user, 'teacher_profile'):
        schedules = LiveClassSchedule.objects.filter(
            teacher=user.teacher_profile,
            is_active=True
        )
    elif hasattr(user, 'student_profile'):
        schedules = LiveClassSchedule.objects.filter(
            student=user.student_profile,
            is_active=True
        )
    else:
        return Response([])
    
    upcoming = []
    for schedule in schedules:
        next_class = schedule.get_next_class_date()
        if next_class:
            upcoming.append({
                'schedule_id': schedule.schedule_id,
                'subject': schedule.subject,
                'teacher_name': schedule.teacher.full_name,
                'student_name': schedule.student.full_name,
                'scheduled_time': next_class.isoformat(),
                'duration': schedule.class_duration,
                'is_demo': not schedule.demo_completed
            })
    
    # Sort by scheduled time
    upcoming.sort(key=lambda x: x['scheduled_time'])
    
    return Response(upcoming[:10])  # Return next 10 classes