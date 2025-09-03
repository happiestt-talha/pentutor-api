# models.py
from django.db import models
# from django.conf import settings
from authentication.models import User
import re
from django.core.exceptions import ValidationError

# User= settings.AUTH_USER_MODEL

class ChatRoom(models.Model):
    ROOM_TYPES = [
        ('course', 'Course Discussion'),
        ('meeting', 'Meeting Chat'),
        ('job', 'Job Discussion'),
        ('general', 'General Chat')
    ]
    
    name = models.CharField(max_length=255)
    room_type = models.CharField(max_length=20, choices=ROOM_TYPES)
    description = models.TextField(blank=True)
    
    participants = models.ManyToManyField(User, related_name='chat_rooms', blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Reference fields for linking to specific entities
    course_id = models.IntegerField(null=True, blank=True)  # Link to course
    meeting_id = models.IntegerField(null=True, blank=True)  # Link to meeting
    job_id = models.IntegerField(null=True, blank=True)  # Link to job
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_rooms',null=True,blank=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.name} ({self.get_room_type_display()})"


class Message(models.Model):
    MESSAGE_TYPES = [
        ('text', 'Text Message'),
        ('file', 'File Attachment'),
        ('image', 'Image'),
    ]
    
    STATUS_CHOICES = [
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('read', 'Read'),
        ('blocked', 'Blocked'),  # For messages with forbidden content
    ]
    
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES, default='text')
    content = models.TextField()
    original_content = models.TextField(blank=True)  # Store original before filtering
    file_url = models.URLField(blank=True, null=True)
    file_name = models.CharField(max_length=255, blank=True)
    
    # Message status and moderation
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='sent')
    is_edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)
    has_forbidden_content = models.BooleanField(default=False)
    blocked_content_type = models.CharField(max_length=50, blank=True)  # email, phone, social_link
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
    
    def clean(self):
        """Validate message content for forbidden information"""
        if self.content:
            self.original_content = self.content
            forbidden_patterns = self.detect_forbidden_content(self.content)
            
            if forbidden_patterns:
                self.has_forbidden_content = True
                self.blocked_content_type = ', '.join(forbidden_patterns.keys())
                self.status = 'blocked'
                # Replace forbidden content with placeholders
                self.content = self.filter_content(self.content, forbidden_patterns)
    
    def detect_forbidden_content(self, text):
        """Detect forbidden content patterns"""
        patterns = {
            'email': [
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                r'\b[A-Za-z0-9._%+-]+\s*@\s*[A-Za-z0-9.-]+\s*\.\s*[A-Z|a-z]{2,}\b',
                r'\b[A-Za-z0-9._%+-]+\s*at\s*[A-Za-z0-9.-]+\s*dot\s*[A-Z|a-z]{2,}\b'
            ],
            'phone': [
                r'\b(\+92|0)?[0-9]{10,11}\b',  # Pakistani numbers
                r'\b(\+\d{1,3})?[\s.-]?\(?\d{1,4}\)?[\s.-]?\d{1,4}[\s.-]?\d{1,9}\b',
                r'\b\d{4}[\s.-]\d{7}\b',  # 0300-1234567 format
                r'\b\d{3}[\s.-]\d{3}[\s.-]\d{4}\b'  # 300-123-4567 format
            ],
            'social_link': [
                r'\b(?:https?://)?(?:www\.)?(?:facebook|fb)\.com/[A-Za-z0-9._-]+',
                r'\b(?:https?://)?(?:www\.)?instagram\.com/[A-Za-z0-9._-]+',
                r'\b(?:https?://)?(?:www\.)?twitter\.com/[A-Za-z0-9._-]+',
                r'\b(?:https?://)?(?:www\.)?linkedin\.com/in/[A-Za-z0-9._-]+',
                r'\b(?:https?://)?(?:www\.)?youtube\.com/[A-Za-z0-9._-]+',
                r'\b(?:https?://)?(?:www\.)?tiktok\.com/@[A-Za-z0-9._-]+',
                r'\b(?:https?://)?(?:www\.)?snapchat\.com/add/[A-Za-z0-9._-]+',
                r'\bwww\.[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                r'\b[A-Za-z0-9.-]+\.(com|net|org|edu|gov)\b'
            ]
        }
        
        found_patterns = {}
        for content_type, regex_list in patterns.items():
            for pattern in regex_list:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    if content_type not in found_patterns:
                        found_patterns[content_type] = []
                    found_patterns[content_type].extend(matches)
        
        return found_patterns
    
    def filter_content(self, text, forbidden_patterns):
        """Replace forbidden content with placeholders"""
        filtered_text = text
        
        for content_type, matches in forbidden_patterns.items():
            if content_type == 'email':
                filtered_text = re.sub(
                    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                    '[EMAIL HIDDEN]',
                    filtered_text,
                    flags=re.IGNORECASE
                )
            elif content_type == 'phone':
                filtered_text = re.sub(
                    r'\b(\+92|0)?[0-9]{10,11}\b',
                    '[PHONE NUMBER HIDDEN]',
                    filtered_text
                )
                filtered_text = re.sub(
                    r'\b(\+\d{1,3})?[\s.-]?\(?\d{1,4}\)?[\s.-]?\d{1,4}[\s.-]?\d{1,9}\b',
                    '[PHONE NUMBER HIDDEN]',
                    filtered_text
                )
            elif content_type == 'social_link':
                filtered_text = re.sub(
                    r'\b(?:https?://)?(?:www\.)?(?:facebook|fb|instagram|twitter|linkedin|youtube|tiktok|snapchat)\.com/[A-Za-z0-9._/-]+',
                    '[SOCIAL LINK HIDDEN]',
                    filtered_text,
                    flags=re.IGNORECASE
                )
        
        return filtered_text
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.sender.username} in {self.room.name}: {self.content[:50]}..."


class MessageRead(models.Model):
    """Track message read status for each user"""
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='read_by')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    read_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['message', 'user']
    
    def __str__(self):
        return f"{self.user.username} read {self.message.id}"
