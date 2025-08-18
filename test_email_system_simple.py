#!/usr/bin/env python
"""
Simple test script for email automation system (without Celery/Redis)
Run this script to verify that the email templates and basic functionality work
"""

import os
import sys
import django

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lms.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from django.template import Template, Context
from courses.models import Course, Enrollment
from payments.models import Payment
from email_automation.models import EmailTemplate, EmailLog, EmailPreference
from django.utils import timezone

User = get_user_model()

def test_email_templates():
    """Test email templates and basic functionality"""
    print("🧪 Testing Email Automation System (Simple)")
    print("=" * 50)
    
    # Check if email templates exist
    print("\n1. Checking Email Templates...")
    templates = EmailTemplate.objects.all()
    if templates.exists():
        print(f"✅ Found {templates.count()} email templates:")
        for template in templates:
            print(f"   - {template.name} ({template.email_type})")
            
        # Test template rendering
        print("\n2. Testing Template Rendering...")
        enrollment_template = EmailTemplate.objects.filter(email_type='enrollment').first()
        if enrollment_template:
            # Get test user and course for proper context
            test_user = User.objects.first()
            test_course = Course.objects.first()
            
            # Test context with actual objects
            context = {
                'user': test_user,
                'course': test_course,
                'site_name': 'LMS Platform'
            }
            
            # Render subject
            subject_template = Template(enrollment_template.subject)
            rendered_subject = subject_template.render(Context(context))
            print(f"   ✅ Subject: {rendered_subject}")
            
            # Render HTML content
            html_template = Template(enrollment_template.html_content)
            rendered_html = html_template.render(Context(context))
            print(f"   ✅ HTML content rendered successfully (length: {len(rendered_html)} chars)")
            
            # Show a preview of the rendered content
            print("\n   📧 Email Preview:")
            print(f"   Subject: {rendered_subject}")
            print("   Content (first 200 chars):")
            print(f"   {rendered_html[:200]}...")
            
    else:
        print("❌ No email templates found. Run: python manage.py setup_email_automation")
        return False
    
    # Check users and email preferences
    print("\n3. Checking User Email Preferences...")
    users = User.objects.all()
    if users.exists():
        print(f"✅ Found {users.count()} users")
        preferences_count = EmailPreference.objects.count()
        print(f"✅ Found {preferences_count} email preference records")
        
        # Show sample user preferences
        sample_pref = EmailPreference.objects.first()
        if sample_pref:
            print(f"   Sample preferences for {sample_pref.user.email}:")
            print(f"   - Enrollment emails: {sample_pref.enrollment_emails}")
            print(f"   - Progress emails: {sample_pref.progress_emails}")
            print(f"   - Payment emails: {sample_pref.payment_emails}")
            print(f"   - Content emails: {sample_pref.content_emails}")
            print(f"   - Demo emails: {sample_pref.demo_emails}")
    else:
        print("❌ No users found.")
        return False
    
    # Test email creation (without sending)
    print("\n4. Testing Email Creation...")
    try:
        test_user = users.first()
        
        # Create a test email log entry
        email_log = EmailLog.objects.create(
            recipient=test_user,
            email_type='enrollment',
            subject='Test Enrollment Email',
            content='This is a test email content',
            status='sent',
            sent_at=timezone.now()
        )
        
        print(f"   ✅ Created test email log: {email_log}")
        
        # Clean up
        email_log.delete()
        print("   ✅ Cleaned up test data")
        
    except Exception as e:
        print(f"   ❌ Error creating test email: {str(e)}")
        return False
    
    # Show available courses
    print("\n5. Available Courses for Testing...")
    courses = Course.objects.all()
    if courses.exists():
        print(f"✅ Found {courses.count()} courses:")
        for course in courses[:3]:  # Show first 3
            print(f"   - {course.title} (${course.price})")
    else:
        print("❌ No courses found.")
    
    print("\n" + "=" * 50)
    print("🎉 Email system basic test completed!")
    print("\n📋 System Status:")
    print(f"   ✅ Email templates: {EmailTemplate.objects.count()}")
    print(f"   ✅ Users: {User.objects.count()}")
    print(f"   ✅ Email preferences: {EmailPreference.objects.count()}")
    print(f"   ✅ Courses: {Course.objects.count()}")
    print(f"   ✅ Email logs: {EmailLog.objects.count()}")
    
    print("\n🚀 Next steps to fully activate the system:")
    print("1. Install and start Redis: sudo apt install redis-server && sudo systemctl start redis")
    print("2. Start Celery worker: celery -A lms worker -l info")
    print("3. Start Celery beat: celery -A lms beat -l info")
    print("4. Configure email settings in settings.py for production")
    print("5. Test the API endpoints: /api/email-automation/")
    
    return True

if __name__ == "__main__":
    test_email_templates()