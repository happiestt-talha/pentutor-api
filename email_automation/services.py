import logging
from typing import Dict, Any, Optional, List
from django.core.mail import EmailMultiAlternatives
from django.template import Template, Context
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model

from .models import EmailTemplate, EmailLog, EmailPreference, EmailQueue

User = get_user_model()
logger = logging.getLogger(__name__)


class EmailService:
    """Service class for handling email operations"""
    
    def __init__(self):
        self.from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@lms.com')
    
    def send_email(
        self,
        recipient: User, # type: ignore
        email_type: str,
        context: Dict[str, Any] = None,
        course=None,
        enrollment=None,
        payment=None
    ) -> bool:
        """
        Send an email to a user based on email type
        
        Args:
            recipient: User to send email to
            email_type: Type of email (enrollment, demo_completed, etc.)
            context: Template context variables
            course: Related course object
            enrollment: Related enrollment object
            payment: Related payment object
        
        Returns:
            bool: True if email was sent successfully
        """
        try:
            # Check if user can receive this email type
            if not self._can_send_email(recipient, email_type):
                logger.info(f"User {recipient.email} has opted out of {email_type} emails")
                return False
            
            # Get email template
            template = self._get_template(email_type)
            if not template:
                logger.error(f"No template found for email type: {email_type}")
                return False
            
            # Prepare context
            if context is None:
                context = {}
            
            context.update({
                'user': recipient,
                'course': course,
                'enrollment': enrollment,
                'payment': payment,
                'site_name': getattr(settings, 'SITE_NAME', 'LMS Platform'),
                'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
            })
            
            # Render email content
            subject = self._render_template(template.subject, context)
            html_content = self._render_template(template.html_content, context)
            text_content = self._render_template(template.text_content, context) if template.text_content else None
            
            # Create email log entry
            email_log = EmailLog.objects.create(
                recipient=recipient,
                email_type=email_type,
                subject=subject,
                content=html_content,
                course=course,
                enrollment=enrollment,
                payment=payment
            )
            
            # Send email
            success = self._send_email_message(
                recipient.email,
                subject,
                html_content,
                text_content
            )
            
            # Update log
            if success:
                email_log.status = 'sent'
                email_log.sent_at = timezone.now()
            else:
                email_log.status = 'failed'
                email_log.error_message = "Failed to send email"
            
            email_log.save()
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending email to {recipient.email}: {str(e)}")
            return False
    
    def queue_email(
        self,
        recipient: User,
        email_type: str,
        scheduled_at: timezone.datetime,
        context: Dict[str, Any] = None,
        priority: str = 'normal'
    ) -> EmailQueue:
        """
        Queue an email for later sending
        
        Args:
            recipient: User to send email to
            email_type: Type of email
            scheduled_at: When to send the email
            context: Template context variables
            priority: Email priority (low, normal, high, urgent)
        
        Returns:
            EmailQueue: Created queue entry
        """
        template = self._get_template(email_type)
        if not template:
            raise ValueError(f"No template found for email type: {email_type}")
        
        if context is None:
            context = {}
        
        # Render subject and content with basic context
        basic_context = {
            'user': recipient,
            'site_name': getattr(settings, 'SITE_NAME', 'LMS Platform'),
        }
        basic_context.update(context)
        
        subject = self._render_template(template.subject, basic_context)
        content = self._render_template(template.html_content, basic_context)
        
        return EmailQueue.objects.create(
            recipient=recipient,
            email_type=email_type,
            subject=subject,
            content=content,
            scheduled_at=scheduled_at,
            priority=priority,
            context_data=context
        )
    
    def send_bulk_email(
        self,
        recipients: List[User],
        email_type: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, int]:
        """
        Send bulk emails to multiple users
        
        Args:
            recipients: List of users to send email to
            email_type: Type of email
            context: Template context variables
        
        Returns:
            Dict with success and failure counts
        """
        results = {'success': 0, 'failed': 0}
        
        for recipient in recipients:
            if self.send_email(recipient, email_type, context):
                results['success'] += 1
            else:
                results['failed'] += 1
        
        return results
    
    def _can_send_email(self, user: User, email_type: str) -> bool:
        """Check if user can receive this type of email"""
        try:
            preference = EmailPreference.objects.get(user=user)
            return preference.can_receive_email(email_type)
        except EmailPreference.DoesNotExist:
            # Create default preferences if they don't exist
            EmailPreference.objects.create(user=user)
            return True
    
    def _get_template(self, email_type: str) -> Optional[EmailTemplate]:
        """Get email template by type"""
        try:
            return EmailTemplate.objects.get(email_type=email_type, is_active=True)
        except EmailTemplate.DoesNotExist:
            return None
    
    def _render_template(self, template_string: str, context: Dict[str, Any]) -> str:
        """Render Django template string with context"""
        template = Template(template_string)
        return template.render(Context(context))
    
    def _send_email_message(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str = None
    ) -> bool:
        """Send the actual email message"""
        try:
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_content or html_content,
                from_email=self.from_email,
                to=[to_email]
            )
            
            if html_content:
                msg.attach_alternative(html_content, "text/html")
            
            msg.send()
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False


class EmailTemplateService:
    """Service for managing email templates"""
    
    @staticmethod
    def create_default_templates():
        """Create default email templates"""
        templates = [
            {
                'name': 'Course Enrollment Welcome',
                'email_type': 'enrollment',
                'subject': '🎉 Welcome to {{ course.title }}!',
                'html_content': '''
                <html>
                <body>
                    <h2>🎉 Congratulations!</h2>
                    <p>Dear {{ user.first_name|default:user.username }},</p>
                    <p>You've successfully joined our course <strong>{{ course.title }}</strong>!</p>
                    <p>Please proceed with the payment. The course fee is <strong>${{ course.price }}</strong>.</p>
                    <p>Course Details:</p>
                    <ul>
                        <li><strong>Course:</strong> {{ course.title }}</li>
                        <li><strong>Instructor:</strong> {{ course.teacher.user.get_full_name|default:course.teacher.user.username }}</li>
                        <li><strong>Price:</strong> ${{ course.price }}</li>
                    </ul>
                    <p>We're excited to have you on this learning journey!</p>
                    <p>Best regards,<br>{{ site_name }} Team</p>
                </body>
                </html>
                ''',
                'text_content': '''
                🎉 Congratulations!
                
                Dear {{ user.first_name|default:user.username }},
                
                You've successfully joined our course {{ course.title }}!
                Please proceed with the payment. The course fee is ${{ course.price }}.
                
                Course Details:
                - Course: {{ course.title }}
                - Instructor: {{ course.teacher.user.get_full_name|default:course.teacher.user.username }}
                - Price: ${{ course.price }}
                
                We're excited to have you on this learning journey!
                
                Best regards,
                {{ site_name }} Team
                '''
            },
            {
                'name': 'Demo Class Completed',
                'email_type': 'demo_completed',
                'subject': 'Demo Class Completed - Next Steps',
                'html_content': '''
                <html>
                <body>
                    <h2>Thank you for attending the demo class!</h2>
                    <p>Dear {{ user.first_name|default:user.username }},</p>
                    <p>You have successfully attended your demo class for <strong>{{ course.title }}</strong>.</p>
                    <p>To continue the course and access all materials, please complete the payment.</p>
                    <p>Course fee: <strong>${{ course.price }}</strong></p>
                    <p>What you'll get after payment:</p>
                    <ul>
                        <li>Access to all course videos and materials</li>
                        <li>Live classes and recordings</li>
                        <li>Assignments and quizzes</li>
                        <li>Direct interaction with instructors</li>
                        <li>Certificate upon completion</li>
                    </ul>
                    <p>Don't miss out on this opportunity to enhance your skills!</p>
                    <p>Best regards,<br>{{ site_name }} Team</p>
                </body>
                </html>
                ''',
                'text_content': '''
                Thank you for attending the demo class!
                
                Dear {{ user.first_name|default:user.username }},
                
                You have successfully attended your demo class for {{ course.title }}.
                To continue the course and access all materials, please complete the payment.
                
                Course fee: ${{ course.price }}
                
                What you'll get after payment:
                - Access to all course videos and materials
                - Live classes and recordings
                - Assignments and quizzes
                - Direct interaction with instructors
                - Certificate upon completion
                
                Don't miss out on this opportunity to enhance your skills!
                
                Best regards,
                {{ site_name }} Team
                '''
            },
            {
                'name': 'Payment Confirmation',
                'email_type': 'payment_confirmation',
                'subject': '✅ Payment Confirmed - Welcome to {{ course.title }}!',
                'html_content': '''
                <html>
                <body>
                    <h2>✅ Payment received!</h2>
                    <p>Dear {{ user.first_name|default:user.username }},</p>
                    <p>Welcome officially to <strong>{{ course.title }}</strong>!</p>
                    <p>Your payment of <strong>${{ payment.amount }}</strong> has been successfully processed.</p>
                    <p>Payment Details:</p>
                    <ul>
                        <li><strong>Amount:</strong> ${{ payment.amount }}</li>
                        <li><strong>Transaction ID:</strong> {{ payment.txn_ref }}</li>
                        <li><strong>Payment Method:</strong> {{ payment.get_gateway_display }}</li>
                        <li><strong>Date:</strong> {{ payment.created_at|date:"F d, Y" }}</li>
                    </ul>
                    <p>You now have full access to:</p>
                    <ul>
                        <li>All course videos and materials</li>
                        <li>Live classes</li>
                        <li>Assignments and quizzes</li>
                        <li>Course community</li>
                    </ul>
                    <p>We wish you a great learning journey!</p>
                    <p>Best regards,<br>{{ site_name }} Team</p>
                </body>
                </html>
                ''',
                'text_content': '''
                ✅ Payment received!
                
                Dear {{ user.first_name|default:user.username }},
                
                Welcome officially to {{ course.title }}!
                Your payment of ${{ payment.amount }} has been successfully processed.
                
                Payment Details:
                - Amount: ${{ payment.amount }}
                - Transaction ID: {{ payment.txn_ref }}
                - Payment Method: {{ payment.get_gateway_display }}
                - Date: {{ payment.created_at|date:"F d, Y" }}
                
                You now have full access to:
                - All course videos and materials
                - Live classes
                - Assignments and quizzes
                - Course community
                
                We wish you a great learning journey!
                
                Best regards,
                {{ site_name }} Team
                '''
            },
            {
                'name': 'Weekly Progress Report',
                'email_type': 'weekly_progress',
                'subject': '📈 Your Weekly Progress in {{ course.title }}',
                'html_content': '''
                <html>
                <body>
                    <h2>📈 Your weekly progress</h2>
                    <p>Dear {{ user.first_name|default:user.username }},</p>
                    <p>Here's your progress summary for <strong>{{ course.title }}</strong> this week:</p>
                    
                    <div style="background-color: #f5f5f5; padding: 20px; border-radius: 5px; margin: 20px 0;">
                        <h3>Progress Summary</h3>
                        <ul>
                            <li><strong>Videos:</strong> {{ progress_report.videos_completed }} out of {{ progress_report.total_videos }} completed</li>
                            <li><strong>Quizzes:</strong> {{ progress_report.quizzes_completed }} out of {{ progress_report.total_quizzes }} completed</li>
                            <li><strong>Assignments:</strong> {{ progress_report.assignments_completed }} out of {{ progress_report.total_assignments }} completed</li>
                            <li><strong>Overall Progress:</strong> {{ progress_report.completion_percentage }}%</li>
                        </ul>
                    </div>
                    
                    <p>{% if progress_report.completion_percentage >= 80 %}
                        🎉 Excellent work! You're making great progress!
                    {% elif progress_report.completion_percentage >= 50 %}
                        👍 Good job! Keep up the momentum!
                    {% else %}
                        💪 You can do it! Try to spend more time on the course this week.
                    {% endif %}</p>
                    
                    <p>Keep it up and continue your learning journey!</p>
                    <p>Best regards,<br>{{ site_name }} Team</p>
                </body>
                </html>
                ''',
                'text_content': '''
                📈 Your weekly progress
                
                Dear {{ user.first_name|default:user.username }},
                
                Here's your progress summary for {{ course.title }} this week:
                
                Progress Summary:
                - Videos: {{ progress_report.videos_completed }} out of {{ progress_report.total_videos }} completed
                - Quizzes: {{ progress_report.quizzes_completed }} out of {{ progress_report.total_quizzes }} completed
                - Assignments: {{ progress_report.assignments_completed }} out of {{ progress_report.total_assignments }} completed
                - Overall Progress: {{ progress_report.completion_percentage }}%
                
                {% if progress_report.completion_percentage >= 80 %}
                🎉 Excellent work! You're making great progress!
                {% elif progress_report.completion_percentage >= 50 %}
                👍 Good job! Keep up the momentum!
                {% else %}
                💪 You can do it! Try to spend more time on the course this week.
                {% endif %}
                
                Keep it up and continue your learning journey!
                
                Best regards,
                {{ site_name }} Team
                '''
            },
            {
                'name': 'New Content Notification',
                'email_type': 'new_content',
                'subject': '🎥 New content added to {{ course.title }}!',
                'html_content': '''
                <html>
                <body>
                    <h2>🎥 New content added!</h2>
                    <p>Dear {{ user.first_name|default:user.username }},</p>
                    <p>Great news! New content has been added to your course <strong>{{ course.title }}</strong>.</p>
                    
                    <div style="background-color: #e8f5e8; padding: 20px; border-radius: 5px; margin: 20px 0;">
                        <h3>What's New:</h3>
                        <p>{{ new_content_description|default:"New videos, lessons, and materials are now available!" }}</p>
                    </div>
                    
                    <p>Check it out in your LMS dashboard and continue your learning journey!</p>
                    <p>Don't miss out on the latest updates and enhancements to your course.</p>
                    
                    <p>Happy learning!</p>
                    <p>Best regards,<br>{{ site_name }} Team</p>
                </body>
                </html>
                ''',
                'text_content': '''
                🎥 New content added!
                
                Dear {{ user.first_name|default:user.username }},
                
                Great news! New content has been added to your course {{ course.title }}.
                
                What's New:
                {{ new_content_description|default:"New videos, lessons, and materials are now available!" }}
                
                Check it out in your LMS dashboard and continue your learning journey!
                Don't miss out on the latest updates and enhancements to your course.
                
                Happy learning!
                
                Best regards,
                {{ site_name }} Team
                '''
            }
        ]
        
        for template_data in templates:
            EmailTemplate.objects.get_or_create(
                email_type=template_data['email_type'],
                defaults=template_data
            )