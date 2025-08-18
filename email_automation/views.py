from django.shortcuts import render
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404

from courses.models import Course, Enrollment
from payments.models import Payment
from .models import EmailTemplate, EmailLog, EmailPreference
from .services import EmailService
from .tasks import (
    send_enrollment_email,
    send_payment_confirmation_email,
    send_demo_completed_email,
    generate_weekly_progress_reports,
    send_new_content_notification
)

User = get_user_model()


class EmailAutomationViewSet(viewsets.ViewSet):
    """
    ViewSet for managing email automation
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'], permission_classes=[IsAdminUser])
    def test_enrollment_email(self, request):
        """Test enrollment email sending"""
        user_id = request.data.get('user_id')
        course_id = request.data.get('course_id')
        
        if not user_id or not course_id:
            return Response(
                {'error': 'user_id and course_id are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = get_object_or_404(User, id=user_id)
            course = get_object_or_404(Course, id=course_id)
            enrollment, created = Enrollment.objects.get_or_create(
                student=user, 
                course=course,
                defaults={'enrolled_at': timezone.now()}
            )
            
            # Send email asynchronously
            send_enrollment_email.delay(user_id, course_id, enrollment.id)
            
            return Response({
                'message': 'Enrollment email queued successfully',
                'enrollment_created': created
            })
            
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'], permission_classes=[IsAdminUser])
    def test_payment_email(self, request):
        """Test payment confirmation email sending"""
        user_id = request.data.get('user_id')
        course_id = request.data.get('course_id')
        
        if not user_id or not course_id:
            return Response(
                {'error': 'user_id and course_id are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = get_object_or_404(User, id=user_id)
            course = get_object_or_404(Course, id=course_id)
            enrollment = get_object_or_404(Enrollment, student=user, course=course)
            
            # Create a test payment record
            payment, created = Payment.objects.get_or_create(
                student=user,
                course=course,
                defaults={
                    'amount': course.price,
                    'payment_status': 'completed',
                    'payment_date': timezone.now()
                }
            )
            
            # Send email asynchronously
            send_payment_confirmation_email.delay(user_id, course_id, payment.id)
            
            return Response({
                'message': 'Payment confirmation email queued successfully',
                'payment_created': created
            })
            
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'], permission_classes=[IsAdminUser])
    def trigger_weekly_reports(self, request):
        """Manually trigger weekly progress reports"""
        try:
            generate_weekly_progress_reports.delay()
            return Response({'message': 'Weekly progress reports queued successfully'})
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'], permission_classes=[IsAdminUser])
    def test_new_content_email(self, request):
        """Test new content notification email"""
        course_id = request.data.get('course_id')
        content_type = request.data.get('content_type', 'video')
        content_title = request.data.get('content_title', 'New Test Content')
        
        if not course_id:
            return Response(
                {'error': 'course_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            course = get_object_or_404(Course, id=course_id)
            send_new_content_notification.delay(course_id, content_type, content_title)
            
            return Response({
                'message': 'New content notification emails queued successfully'
            })
            
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def email_logs(self, request):
        """Get email logs for the current user"""
        logs = EmailLog.objects.filter(recipient=request.user).order_by('-sent_at')[:50]
        
        log_data = []
        for log in logs:
            log_data.append({
                'id': log.id,
                'email_type': log.get_email_type_display(),
                'subject': log.subject,
                'status': log.get_status_display(),
                'sent_at': log.sent_at,
                'delivered_at': log.delivered_at,
                'opened_at': log.opened_at
            })
        
        return Response({'logs': log_data})
    
    @action(detail=False, methods=['get', 'post'])
    def preferences(self, request):
        """Get or update email preferences for the current user"""
        preference, created = EmailPreference.objects.get_or_create(
            user=request.user
        )
        
        if request.method == 'GET':
            return Response({
                'enrollment_emails': preference.enrollment_emails,
                'progress_emails': preference.progress_emails,
                'payment_emails': preference.payment_emails,
                'content_emails': preference.content_emails,
                'demo_emails': preference.demo_emails
            })
        
        elif request.method == 'POST':
            # Update preferences
            preference.enrollment_emails = request.data.get('enrollment_emails', preference.enrollment_emails)
            preference.progress_emails = request.data.get('progress_emails', preference.progress_emails)
            preference.payment_emails = request.data.get('payment_emails', preference.payment_emails)
            preference.content_emails = request.data.get('content_emails', preference.content_emails)
            preference.demo_emails = request.data.get('demo_emails', preference.demo_emails)
            preference.save()
            
            return Response({'message': 'Email preferences updated successfully'})
