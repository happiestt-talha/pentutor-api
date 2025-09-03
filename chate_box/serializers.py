
# serializers.py
from rest_framework import serializers
# from django.conf import  settings
from authentication.models import User
from .models import ChatRoom, Message, MessageRead

# User=settings.AUTH_USER_MODEL

class ChatUserSerializer(serializers.ModelSerializer):
    user_type = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    profile_picture = serializers.SerializerMethodField() 
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'full_name', 'user_type','role','profile_picture']
    
    def get_user_type(self, obj):
        # Assuming you have Teacher and Student models linked to User
        if hasattr(obj, 'teacher_profile'):
            return 'teacher'
        elif hasattr(obj, 'student_profile'):
            return 'student'
        return 'user'
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username

    def get_profile_picture(self, obj):
        # Teacher profile ka pic
        if hasattr(obj, 'teacher_profile') and obj.teacher_profile.profile_picture:
            return obj.teacher_profile.profile_picture.url
        
        # Student profile ka pic
        if hasattr(obj, 'student_profile') and obj.student_profile.profile_picture:
            return obj.student_profile.profile_picture.url
        
        # Default agar kuch na mila
        return None


class MessageSerializer(serializers.ModelSerializer):
    sender = ChatUserSerializer(read_only=True)
    read_by_users = serializers.SerializerMethodField()
    is_read_by_me = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = [
            'id', 'room', 'sender', 'message_type', 'content', 'original_content',
            'file_url', 'file_name', 'status', 'is_edited', 'edited_at',
            'has_forbidden_content', 'blocked_content_type', 'created_at',
            'updated_at', 'read_by_users', 'is_read_by_me'
        ]
        read_only_fields = [
            'sender', 'original_content', 'status', 'has_forbidden_content',
            'blocked_content_type', 'created_at', 'updated_at'
        ]
    
    def get_read_by_users(self, obj):
        return obj.read_by.values_list('user__username', flat=True)
    
    def get_is_read_by_me(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.read_by.filter(user=request.user).exists()
        return False
    
    def create(self, validated_data):
        validated_data['sender'] = self.context['request'].user
        return super().create(validated_data)


class ChatRoomSerializer(serializers.ModelSerializer):
    # created_by = ChatUserSerializer(read_only=True)
    participants = ChatUserSerializer(many=True, read_only=True)
    participants_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False
    )
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    total_messages = serializers.SerializerMethodField()
    created_by = ChatUserSerializer(read_only=True)
    
    class Meta:
        model = ChatRoom
        fields = [
            'id', 'name', 'room_type', 'description', 'created_by',
            'participants', 'participants_ids', 'is_active', 'created_at',
            'updated_at', 'course_id', 'meeting_id', 'job_id',
            'last_message', 'unread_count', 'total_messages'
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at']
    
    def get_last_message(self, obj):
        last_message = obj.messages.filter(status__in=['sent', 'delivered', 'read']).last()
        if last_message:
            return {
                'id': last_message.id,
                'content': last_message.content[:100],
                'sender': last_message.sender.username,
                'created_at': last_message.created_at,
                'message_type': last_message.message_type
            }
        return None
    
    def get_unread_count(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.messages.filter(
                status__in=['sent', 'delivered']
            ).exclude(
                read_by__user=request.user
            ).exclude(
                sender=request.user
            ).count()
        return 0
    
    def get_total_messages(self, obj):
        return obj.messages.filter(status__in=['sent', 'delivered', 'read']).count()
    
    def create(self, validated_data):
        participants_ids = validated_data.pop('participants_ids', [])
        validated_data['created_by'] = self.context['request'].user
        
        room = super().create(validated_data)
        
        # Add participants
        if participants_ids:
            
            users = User.objects.filter(id__in=participants_ids)
            room.participants.set(users)
        
        # Add creator as participant
        room.participants.add(self.context['request'].user)
        
        return room

