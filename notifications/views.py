# notifications/views.py

from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404
from .models import Notification
from .serializers import (
    NotificationSerializer,
    NotificationListSerializer,
    MarkAsReadSerializer,
    NotificationStatsSerializer
)


class NotificationPagination(PageNumberPagination):
    """Custom pagination for notifications"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class NotificationListView(generics.ListAPIView):
    """
    Get all notifications for the logged-in user
    
    Query Parameters:
    - is_read: Filter by read status (true/false)
    - notification_type: Filter by notification type
    - page: Page number for pagination
    - page_size: Number of items per page (max 100)
    """
    serializer_class = NotificationListSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = NotificationPagination
    
    def get_queryset(self):
        user = self.request.user
        queryset = Notification.objects.filter(recipient=user).select_related(
            'sender', 'course', 'video', 'quiz', 'meeting'
        )
        
        # Filter by read status
        is_read = self.request.query_params.get('is_read', None)
        if is_read is not None:
            is_read_bool = is_read.lower() == 'true'
            queryset = queryset.filter(is_read=is_read_bool)
        
        # Filter by notification type
        notification_type = self.request.query_params.get('notification_type', None)
        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)
        
        return queryset


class NotificationDetailView(generics.RetrieveAPIView):
    """
    Get detailed information about a specific notification
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Notification.objects.none()
        return Notification.objects.filter(recipient=self.request.user).select_related(
            'sender', 'course', 'video', 'quiz', 'meeting'
        )
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        # Automatically mark as read when viewed
        if not instance.is_read:
            instance.mark_as_read()
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_notifications_as_read(request):
    """
    Mark one or more notifications as read
    
    POST Body:
    {
        "notification_ids": [1, 2, 3, 4]
    }
    """
    serializer = MarkAsReadSerializer(data=request.data)
    if serializer.is_valid():
        notification_ids = serializer.validated_data['notification_ids']
        
        # Get notifications that belong to the current user and are unread
        notifications = Notification.objects.filter(
            id__in=notification_ids,
            recipient=request.user,
            is_read=False
        )
        
        if not notifications.exists():
            return Response(
                {'error': 'No unread notifications found with the provided IDs.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Mark notifications as read
        updated_count = 0
        for notification in notifications:
            notification.mark_as_read()
            updated_count += 1
        
        return Response({
            'message': f'Successfully marked {updated_count} notifications as read.',
            'updated_count': updated_count
        })
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_all_notifications_as_read(request):
    """
    Mark all unread notifications as read for the current user
    """
    unread_notifications = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    )
    
    updated_count = 0
    for notification in unread_notifications:
        notification.mark_as_read()
        updated_count += 1
    
    return Response({
        'message': f'Successfully marked {updated_count} notifications as read.',
        'updated_count': updated_count
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notification_stats(request):
    """
    Get notification statistics for the current user
    
    Returns:
    - total_count: Total number of notifications
    - unread_count: Number of unread notifications
    - read_count: Number of read notifications
    - notification_types: Count by notification type
    """
    user = request.user
    
    # Get total counts
    total_count = Notification.objects.filter(recipient=user).count()
    unread_count = Notification.objects.filter(recipient=user, is_read=False).count()
    read_count = total_count - unread_count
    
    # Get counts by notification type
    type_counts = Notification.objects.filter(recipient=user).values(
        'notification_type'
    ).annotate(
        count=Count('id')
    ).order_by('notification_type')
    
    notification_types = {item['notification_type']: item['count'] for item in type_counts}
    
    stats_data = {
        'total_count': total_count,
        'unread_count': unread_count,
        'read_count': read_count,
        'notification_types': notification_types
    }
    
    serializer = NotificationStatsSerializer(stats_data)
    return Response(serializer.data)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_notification(request, notification_id):
    """
    Delete a specific notification
    """
    try:
        notification = Notification.objects.get(
            id=notification_id,
            recipient=request.user
        )
        notification.delete()
        return Response({
            'message': 'Notification deleted successfully.'
        })
    except Notification.DoesNotExist:
        return Response(
            {'error': 'Notification not found.'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_all_read_notifications(request):
    """
    Delete all read notifications for the current user
    """
    deleted_count, _ = Notification.objects.filter(
        recipient=request.user,
        is_read=True
    ).delete()
    
    return Response({
        'message': f'Successfully deleted {deleted_count} read notifications.',
        'deleted_count': deleted_count
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def unread_notifications_count(request):
    """
    Get the count of unread notifications for the current user
    This is useful for showing notification badges in the UI
    """
    unread_count = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).count()
    
    return Response({
        'unread_count': unread_count
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recent_notifications(request):
    """
    Get the 10 most recent notifications for the current user
    This is useful for dropdown notification panels
    """
    recent_notifications = Notification.objects.filter(
        recipient=request.user
    ).select_related(
        'sender', 'course'
    ).order_by('-created_at')[:10]
    
    serializer = NotificationListSerializer(recent_notifications, many=True)
    return Response({
        'notifications': serializer.data,
        'count': recent_notifications.count()
    })