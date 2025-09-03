from django.urls import path
from . import views

urlpatterns = [
    # Meeting Management
    path('create/', views.create_meeting, name='create_meeting'),
    path('join/<str:meeting_id>/', views.join_meeting, name='join_meeting'),
    path('leave/<str:meeting_id>/', views.leave_meeting, name='leave_meeting'),
    path('end/<str:meeting_id>/', views.end_meeting, name='end_meeting'),
    path('detail/<str:meeting_id>/', views.meting_detail, name='meeting_detail'),
    
    # Participants
    path('<str:meeting_id>/participants/', views.get_meeting_participants, name='meeting_participants'),
    
    # Access Control & Invitations
    # path('<str:meeting_id>/invites/', views.send_invites, name='send_invites'),
    # path('<str:meeting_id>/join-requests/', views.get_join_requests, name='get_join_requests'),
    # path('<str:meeting_id>/handle-request/', views.handle_join_request, name='handle_join_request'),
    # path('<str:meeting_id>/request-status/<int:request_id>/', views.check_join_request_status, name='check_join_request_status'),
]