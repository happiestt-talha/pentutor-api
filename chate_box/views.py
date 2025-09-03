
# views.py
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Prefetch
from django.shortcuts import get_object_or_404
from .models import ChatRoom, Message, MessageRead
from .serializers import ChatRoomSerializer, MessageSerializer
from django.utils import timezone

class ChatRoomViewSet(viewsets.ModelViewSet):
    serializer_class = ChatRoomSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # ✅ Fix: Prevent Swagger/AnonymousUser UUID error
        if getattr(self, 'swagger_fake_view', False):
            return ChatRoom.objects.none()

        user = self.request.user
        if not user.is_authenticated:
            return ChatRoom.objects.none()

        queryset = ChatRoom.objects.filter(
            Q(participants=user) | Q(created_by=user)
        ).distinct().prefetch_related(
            'participants',
            'created_by',
            Prefetch('messages', queryset=Message.objects.select_related('sender'))
        )
        
        # Filter by room type
        room_type = self.request.query_params.get('room_type')
        if room_type:
            queryset = queryset.filter(room_type=room_type)
        
        # Filter by course, meeting, or job
        course_id = self.request.query_params.get('course_id')
        if course_id:
            queryset = queryset.filter(course_id=course_id)
        
        meeting_id = self.request.query_params.get('meeting_id')
        if meeting_id:
            queryset = queryset.filter(meeting_id=meeting_id)
        
        job_id = self.request.query_params.get('job_id')
        if job_id:
            queryset = queryset.filter(job_id=job_id)
        
        return queryset

        user = self.request.user
        queryset = ChatRoom.objects.filter(
            Q(participants=user) | Q(created_by=user)
        ).distinct().prefetch_related(
            'participants',
            'created_by',
            Prefetch('messages', queryset=Message.objects.select_related('sender'))
        )
        
        # Filter by room type
        room_type = self.request.query_params.get('room_type')
        if room_type:
            queryset = queryset.filter(room_type=room_type)
        
        # Filter by course, meeting, or job
        course_id = self.request.query_params.get('course_id')
        if course_id:
            queryset = queryset.filter(course_id=course_id)
        
        meeting_id = self.request.query_params.get('meeting_id')
        if meeting_id:
            queryset = queryset.filter(meeting_id=meeting_id)
        
        job_id = self.request.query_params.get('job_id')
        if job_id:
            queryset = queryset.filter(job_id=job_id)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def add_participant(self, request, pk=None):
        room = self.get_object()
        user_id = request.data.get('user_id')
        
        if not user_id:
            return Response(
                {'error': 'user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from django.contrib.auth.models import User
            user = User.objects.get(id=user_id)
            room.participants.add(user)
            return Response({'message': 'Participant added successfully'})
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def remove_participant(self, request, pk=None):
        room = self.get_object()
        user_id = request.data.get('user_id')
        
        if not user_id:
            return Response(
                {'error': 'user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from django.contrib.auth.models import User
            user = User.objects.get(id=user_id)
            room.participants.remove(user)
            return Response({'message': 'Participant removed successfully'})
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        room = self.get_object()
        messages = room.messages.filter(
            status__in=['sent', 'delivered', 'read']
        ).select_related('sender').prefetch_related('read_by__user')
        
        # Pagination
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 50))
        start = (page - 1) * page_size
        end = start + page_size
        
        paginated_messages = messages[start:end]
        serializer = MessageSerializer(
            paginated_messages,
            many=True,
            context={'request': request}
        )
        
        return Response({
            'messages': serializer.data,
            'total_count': messages.count(),
            'page': page,
            'has_next': end < messages.count()
        })


class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        room_id = self.request.query_params.get('room_id')
        if room_id:
            # Verify user has access to this room
            room = get_object_or_404(
                ChatRoom,
                id=room_id,
                participants=self.request.user
            )
            return Message.objects.filter(
                room=room,
                status__in=['sent', 'delivered', 'read']
            ).select_related('sender').prefetch_related('read_by__user')
        
        return Message.objects.none()
    
    def create(self, request, *args, **kwargs):
        room_id = request.data.get('room')
        if not room_id:
            return Response(
                {'error': 'room is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify user has access to this room
        try:
            print("Id: ",room_id)
            print("Participent: ",request.user)
            room = ChatRoom.objects.get(
                id=room_id,
                participants=request.user
            )
        except ChatRoom.DoesNotExist:
            return Response(
                {'error': 'Room not found or access denied'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        response = super().create(request, *args, **kwargs)
        
        if response.status_code == status.HTTP_201_CREATED:
            # Update room's updated_at timestamp
            room.updated_at = timezone.now()
            room.save()
        
        return response
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        message = self.get_object()
        
        # Verify user has access to this message's room
        if not message.room.participants.filter(id=request.user.id).exists():
            return Response(
                {'error': 'Access denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        MessageRead.objects.get_or_create(
            message=message,
            user=request.user
        )
        
        return Response({'message': 'Message marked as read'})
    
    @action(detail=False, methods=['post'])
    def mark_room_read(self, request):
        room_id = request.data.get('room_id')
        if not room_id:
            return Response(
                {'error': 'room_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            room = ChatRoom.objects.get(
                id=room_id,
                participants=request.user
            )
        except ChatRoom.DoesNotExist:
            return Response(
                {'error': 'Room not found or access denied'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Mark all unread messages as read
        unread_messages = Message.objects.filter(
            room=room,
            status__in=['sent', 'delivered']
        ).exclude(sender=request.user).exclude(read_by__user=request.user)
        
        read_objects = []
        for message in unread_messages:
            read_objects.append(
                MessageRead(message=message, user=request.user)
            )
        
        MessageRead.objects.bulk_create(read_objects, ignore_conflicts=True)
        
        return Response({'message': 'All messages marked as read'})
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Only allow sender to edit their own messages
        if instance.sender != request.user:
            return Response(
                {'error': 'You can only edit your own messages'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Mark as edited
        instance.is_edited = True
        instance.edited_at = timezone.now()
        
        return super().update(request, *args, **kwargs)

