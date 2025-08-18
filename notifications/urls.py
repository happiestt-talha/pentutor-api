# notifications/urls.py

from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    # List all notifications for the current user
    path('', views.NotificationListView.as_view(), name='notification-list'),
    
    # Get detailed view of a specific notification
    path('<int:pk>/', views.NotificationDetailView.as_view(), name='notification-detail'),
    
    # Mark specific notifications as read
    path('mark-as-read/', views.mark_notifications_as_read, name='mark-as-read'),
    
    # Mark all notifications as read
    path('mark-all-as-read/', views.mark_all_notifications_as_read, name='mark-all-as-read'),
    
    # Get notification statistics
    path('stats/', views.notification_stats, name='notification-stats'),
    
    # Delete a specific notification
    path('<int:notification_id>/delete/', views.delete_notification, name='delete-notification'),
    
    # Delete all read notifications
    path('delete-all-read/', views.delete_all_read_notifications, name='delete-all-read'),
    
    # Get unread notifications count (for badges)
    path('unread-count/', views.unread_notifications_count, name='unread-count'),
    
    # Get recent notifications (for dropdown)
    path('recent/', views.recent_notifications, name='recent-notifications'),
]