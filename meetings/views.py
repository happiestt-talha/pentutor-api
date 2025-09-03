# meetings/views.py
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated,AllowAny
from .serializers import (
    MeetingSerializer, ParticipantSerializer, CreateMeetingSerializer,
    JoinMeetingSerializer, 
    # SendInviteSerializer, HandleJoinRequestSerializer,
    # JoinRequestSerializer, MeetingInviteSerializer
)
from .models import Meeting, Participant, MeetingInvite, JoinRequest
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import random
from authentication.models import User
from django.utils.text import slugify
from django.core.mail import send_mail
from django.conf import settings
from calendersync.utils import create_google_event
from celery import shared_task
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi




# Add this task for scheduling meeting reminders
@shared_task
def send_meeting_reminder(meeting_id):
    """Send meeting reminder when scheduled time arrives"""
    try:
        meeting = Meeting.objects.get(id=meeting_id)
        
        # Send notification to host
        send_meeting_start_notification(meeting.host, meeting, is_host=True)
        
        # For private meetings, send to invited users
        if meeting.access_type == 'private':
            invites = MeetingInvite.objects.filter(meeting=meeting, status='accepted')
            for invite in invites:
                if invite.user:
                    send_meeting_start_notification(invite.user, meeting, is_host=False)
                else:
                    # Send email to non-registered users
                    send_meeting_start_email_to_guest(invite.email, meeting)
        
        # For lecture meetings, notify enrolled students
        elif meeting.meeting_type == 'lecture' and meeting.course:
            enrolled_students = meeting.get_enrolled_students()
            for enrollment in enrolled_students:
                send_meeting_start_notification(enrollment.student, meeting, is_host=False)
        
        # For public meetings, only notify host
        elif meeting.access_type == 'public':
            pass  # Only host gets notification (already sent above)
            
    except Meeting.DoesNotExist:
        print(f"Meeting with id {meeting_id} not found")

def send_meeting_start_notification(user, meeting, is_host=False):
    """Send notification using your notification app"""
    try:
        # Assuming you have a Notification model in your notification app
        from notifications.models import Notification  # Adjust import based on your app structure
        
        if is_host:
            title = "Your Meeting is Starting"
            message = f"Your meeting '{meeting.title}' is scheduled to start now."
        else:
            title = "Meeting is Starting"
            message = f"The meeting '{meeting.title}' you were invited to is starting now."
        
        Notification.objects.create(
            recipient=user,
            title=title,
            message=message,
            notification_type='meeting_start',
            meeting=meeting,
            is_read=False
        )
        
        # Also send email
        send_meeting_start_email(user.email, meeting, is_host)
        
    except Exception as e:
        print(f"Error sending notification: {e}")

def send_meeting_start_email(email, meeting, is_host=False):
    """Send email notification when meeting starts"""
    try:
        if is_host:
            subject = f"Your Meeting '{meeting.title}' is Starting"
            message = f"""
            Hello {meeting.host.get_full_name() or meeting.host.username},
            
            Your meeting is scheduled to start now.
            
            Meeting Details:
            - Title: {meeting.title}
            - Meeting ID: {meeting.meeting_id}
            - Password: {meeting.password if meeting.is_password_required else 'No password required'}
            - Scheduled Time: {meeting.scheduled_time.strftime('%Y-%m-%d %H:%M')}
            
            Join the meeting: http://127.0.0.1:8000/api/meeting/join/{meeting.meeting_id}
            
            Best regards,
            Your Meeting Platform
            """
        else:
            subject = f"Meeting '{meeting.title}' is Starting"
            message = f"""
            Hello,
            
            The meeting you were invited to is starting now.
            
            Meeting Details:
            - Title: {meeting.title}
            - Host: {meeting.host.get_full_name() or meeting.host.username}
            - Meeting ID: {meeting.meeting_id}
            - Password: {meeting.password if meeting.is_password_required else 'No password required'}
            - Scheduled Time: {meeting.scheduled_time.strftime('%Y-%m-%d %H:%M')}
            
            Join the meeting: http://127.0.0.1:8000/api/meeting/join/{meeting.meeting_id}
            
            Best regards,
            Your Meeting Platform
            """
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        
    except Exception as e:
        print(f"Error sending email: {e}")

def send_meeting_start_email_to_guest(email, meeting):
    """Send email to non-registered users"""
    try:
        subject = f"Meeting '{meeting.title}' is Starting"
        message = f"""
        Hello,
        
        The meeting you were invited to is starting now.
        
        Meeting Details:
        - Title: {meeting.title}
        - Host: {meeting.host.get_full_name() or meeting.host.username}
        - Meeting ID: {meeting.meeting_id}
        - Password: {meeting.password if meeting.is_password_required else 'No password required'}
        - Scheduled Time: {meeting.scheduled_time.strftime('%Y-%m-%d %H:%M')}
        
        Join the meeting: http://127.0.0.1:8000/api/meeting/join/{meeting.meeting_id}
        
        Best regards,
        Your Meeting Platform
        """
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        
    except Exception as e:
        print(f"Error sending email to guest: {e}")

def send_meeting_invitation_email(email, meeting, invited_by):
    """Send initial meeting invitation email"""
    try:
        subject = f"You're Invited to '{meeting.title}'"
        
        if meeting.meeting_type == 'instant':
            time_info = "This is an instant meeting starting now."
        else:
            time_info = f"Scheduled for: {meeting.scheduled_time.strftime('%Y-%m-%d %H:%M')}"
        
        message = f"""
        Hello,
        
        You have been invited to join a meeting by {invited_by.get_full_name() or invited_by.username}.
        
        Meeting Details:
        - Title: {meeting.title}
        - Host: {meeting.host.get_full_name() or meeting.host.username}
        - {time_info}
        - Meeting ID: {meeting.meeting_id}
        - Password: {meeting.password if meeting.is_password_required else 'No password required'}
        
        Join the meeting: http://127.0.0.1:8000/pi//meeting/join/{meeting.meeting_id}
        
        Best regards,
        Your Meeting Platform
        """
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        
    except Exception as e:
        print(f"Error sending invitation email: {e}")

def schedule_meeting_reminder(meeting):
    """Schedule a reminder task for when the meeting should start"""
    if meeting.scheduled_time and meeting.meeting_type == 'scheduled':
        # Schedule the reminder task to run at the meeting time
        from django_celery_beat.models import PeriodicTask, CrontabSchedule
        import json
        
        try:
            # Create a one-time task that runs at the scheduled time
            eta = meeting.scheduled_time
            send_meeting_reminder.apply_async(
                args=[meeting.id],
                eta=eta
            )
        except Exception as e:
            print(f"Error scheduling meeting reminder: {e}")

@swagger_auto_schema(
    method='post',
    operation_summary="Create a new meeting",
    tags=["Meetings"],
    request_body=CreateMeetingSerializer
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_meeting(request):
    """Create a new meeting with access control and notifications"""
    serializer = CreateMeetingSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {'errors': serializer.errors}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    data = serializer.validated_data
    is_password_required = data.get('is_password_required', False)
    
    # Create meeting
    meeting = Meeting.objects.create(
        host=request.user,
        title=data.get('title', f'{request.user.username}\'s Meeting'),
        meeting_type=data.get('meeting_type', 'instant'),
        access_type=data.get('access_type', 'public'),
        scheduled_time=data.get('scheduled_time'),
        max_participants=data.get('max_participants', 100),
        is_waiting_room_enabled=data.get('waiting_room', False),
        allow_participant_share_screen=data.get('allow_screen_share', True),
        allow_participant_unmute=data.get('allow_unmute', True),
        enable_chat=data.get('enable_chat', True),
        enable_reactions=data.get('enable_reactions', True),
        is_password_required=is_password_required,
        course_id=data.get('course_id') if data.get('meeting_type') == 'lecture' else None,
        is_recorded=data.get('is_recorded', False)
    )
    print("password:",is_password_required)
    
    # Set custom password if provided
    if data.get('password'):
        meeting.password = data['password']
        meeting.save()
    
    print("Running create_google_event")
    create_google_event(request.user, meeting)
    print("Done create_google_event")
    
    # Create invites for private meetings and send emails
    if meeting.access_type == 'private' and data.get('invites'):
        for email in data['invites']:
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                user = None
            
            MeetingInvite.objects.create(
                meeting=meeting,
                email=email,
                user=user,
                invited_by=request.user
            )
            
            # Send invitation email
            send_meeting_invitation_email(email, meeting, request.user)
    
    # For lecture meetings, notify enrolled students
    if meeting.meeting_type == 'lecture' and meeting.course:
        enrolled_students = meeting.get_enrolled_students()
        for enrollment in enrolled_students:
            send_meeting_invitation_email(enrollment.student, meeting, request.user)
    
    # Host automatically joins as participant
    participant = Participant.objects.create(
        meeting=meeting,
        user=request.user,
        role='host'
    )
    
    # Handle different meeting types
    if meeting.meeting_type == 'instant':
        meeting.start_meeting()
        # Send immediate notification to host for public meetings
        if meeting.access_type == 'public':
            send_meeting_start_notification(request.user.email, meeting, is_host=True)
    elif meeting.meeting_type == 'scheduled':
        # Schedule reminder for when meeting should start
        schedule_meeting_reminder(meeting)
        
        # Send confirmation email to host
        try:
            subject = f"Meeting '{meeting.title}' Scheduled Successfully"
            message = f"""
            Hello {request.user.get_full_name() or request.user.username},
            
            Your meeting has been scheduled successfully.
            
            Meeting Details:
            - Title: {meeting.title}
            - Scheduled Time: {meeting.scheduled_time.strftime('%Y-%m-%d %H:%M')}
            - Meeting ID: {meeting.meeting_id}
            - Password: {meeting.password if meeting.is_password_required else 'No password required'}
            
            You will receive a reminder when it's time to start the meeting.
            
            Meeting Link: http://127.0.0.1:8000/meeting/join/{meeting.meeting_id}
            
            Best regards,
            Your Meeting Platform
            """
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[request.user.email],
                fail_silently=False,
            )
        except Exception as e:
            print(f"Error sending confirmation email: {e}")
    
    return Response({
        'meeting_id': meeting.meeting_id,
        'password': meeting.password,
        'join_url': f'/meeting/join/{meeting.meeting_id}',
        'status': 'created',
        'meeting': MeetingSerializer(meeting).data,
        'participant': ParticipantSerializer(participant).data,
        'message': 'Meeting created successfully'
    }, status=status.HTTP_201_CREATED)


@swagger_auto_schema(
    method='post',
    operation_summary="Join an existing meeting",
    tags=["Meetings"],
    manual_parameters=[
        openapi.Parameter(
            'meeting_id',
            openapi.IN_PATH,
            description="UUID of the meeting",
            type=openapi.TYPE_STRING,
            format=openapi.FORMAT_UUID,
            required=True
        )
    ],
    request_body=JoinMeetingSerializer
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def join_meeting(request, meeting_id):
    """Join an existing meeting with access control"""
    serializer = JoinMeetingSerializer(data=request.data,context={'request':request})
    
    if not serializer.is_valid():
        return Response(
            {'errors': serializer.errors}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        meeting = Meeting.objects.get(meeting_id=meeting_id)
        
        # Check if meeting exists and is active
        if meeting.status == 'ended':
            return Response({
                'error': 'Meeting has ended'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 🔐 Handle password check
        if meeting.is_password_required:
            print("passowrd :",meeting.is_password_required)
            password = serializer.validated_data.get('password', None)
            if not password:
                return Response({
                    'error': 'This meeting requires a password. Please provide one.'
                }, status=status.HTTP_401_UNAUTHORIZED)
            if password != meeting.password:
                return Response({
                    'error': 'Invalid meeting password'
                }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Check max participants
        active_participants = meeting.participants.filter(left_at__isnull=True).count()
        if active_participants >= meeting.max_participants:
            return Response({
                'error': 'Meeting is full'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # # Get or create user
        # name = serializer.validated_data.get('name')
        # email = serializer.validated_data.get('email')
        
        if request.user.is_authenticated:
             user = request.user
        else:
            try:
                # Check if user already exists with this email
                user = User.objects.get(email=user.email)
            except User.DoesNotExist:
                # Create new user
                username = slugify(user.name) + str(random.randint(1000, 9999))
                user = User.objects.create_user(
                    username=username,
                    password=User.objects.make_random_password(),
                    email=user.email
                )

        
        # Check access permissions
        access_granted = False
        
        if meeting.access_type == 'public':
            access_granted = True
        
        elif meeting.access_type == 'private':
            # Check if user is invited
            invite_exists = MeetingInvite.objects.filter(
                meeting=meeting,
                email=user.email
            ).exists()
            
            if invite_exists or user == meeting.host:
                access_granted = True
            else:
                return Response({
                    'error': 'You are not invited to this private meeting'
                }, status=status.HTTP_403_FORBIDDEN)
        
        elif meeting.access_type == 'approval_required':
            # Check if user is host
            if user == meeting.host:
                access_granted = True
            else:
                # Create or get existing join request
                join_request, created = JoinRequest.objects.get_or_create(
                    meeting=meeting,
                    user=user if request.user.is_authenticated else None,
                    defaults={
                        'guest_name': user.username,
                        'guest_email': user.email
                    }
                )
                
                if join_request.status == 'approved':
                    access_granted = True
                elif join_request.status == 'pending':
                    # Notify host about join request
                    notify_host_about_join_request(meeting, join_request)
                    
                    return Response({
                        'status': 'waiting_approval',
                        'message': 'Your join request has been sent to the host. Please wait for approval.',
                        'request_id': join_request.id
                    }, status=status.HTTP_202_ACCEPTED)
                
                elif join_request.status == 'denied':
                    return Response({
                        'error': 'Your join request was denied by the host'
                    }, status=status.HTTP_403_FORBIDDEN)
        
        if not access_granted:
            return Response({
                'error': 'Access denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Check if user already in meeting
        participant, created = Participant.objects.get_or_create(
            meeting=meeting,
            user=user,
            defaults={
                'role': 'participant',
                'guest_name': user.username
            }
        )
        
        # if not created and participant.is_active:
        #     return Response({
        #         'error': 'You are already in this meeting'
        #     }, status=status.HTTP_400_BAD_REQUEST)
        
        # Rejoin if previously left
        if not created:
            participant.left_at = None
            participant.guest_name = user.username
            participant.save()
        
        # Start meeting if host joins
        if meeting.status == 'waiting' and participant.role == 'host':
            meeting.start_meeting()
        
        # Notify other participants
        notify_participant_joined(meeting_id, participant, user)
        
        return Response({
            'participant': ParticipantSerializer(participant).data,
            'meeting': MeetingSerializer(meeting,context={'request': request}).data,
            'message': 'Successfully joined meeting'
        }, status=status.HTTP_200_OK)
        
    except Meeting.DoesNotExist:
        return Response({
            'error': 'Meeting not found'
        }, status=status.HTTP_404_NOT_FOUND)


# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def handle_join_request(request, meeting_id):
#     """Approve or deny join requests (host/co-host only)"""
#     serializer = HandleJoinRequestSerializer(data=request.data)
    
#     if not serializer.is_valid():
#         return Response(
#             {'errors': serializer.errors},
#             status=status.HTTP_400_BAD_REQUEST
#         )
    
#     try:
#         meeting = Meeting.objects.get(meeting_id=meeting_id)
        
#         # Check if user is host or co-host
#         participant = Participant.objects.get(
#             meeting=meeting,
#             user=request.user,
#             role__in=['host', 'co_host'],
#             left_at__isnull=True
#         )
        
#         request_id = serializer.validated_data['request_id']
#         action = serializer.validated_data['action']
        
#         join_request = JoinRequest.objects.get(
#             id=request_id,
#             meeting=meeting,
#             status='pending'
#         )
        
#         if action == 'approve':
#             join_request.approve(request.user)
            
#             # Notify the requester
#             notify_join_request_response(join_request, 'approved')
            
#             message = f"Join request from {join_request.display_name} approved"
        
#         else:  # deny
#             join_request.deny(request.user)
            
#             # Notify the requester
#             notify_join_request_response(join_request, 'denied')
            
#             message = f"Join request from {join_request.display_name} denied"
        
#         return Response({
#             'message': message,
#             'request': JoinRequestSerializer(join_request).data
#         }, status=status.HTTP_200_OK)
        
#     except Meeting.DoesNotExist:
#         return Response({
#             'error': 'Meeting not found'
#         }, status=status.HTTP_404_NOT_FOUND)
    
#     except Participant.DoesNotExist:
#         return Response({
#             'error': 'Only host or co-host can handle join requests'
#         }, status=status.HTTP_403_FORBIDDEN)
    
#     except JoinRequest.DoesNotExist:
#         return Response({
#             'error': 'Join request not found'
#         }, status=status.HTTP_404_NOT_FOUND)


# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def get_join_requests(request, meeting_id):
#     """Get pending join requests for a meeting (host/co-host only)"""
#     try:
#         meeting = Meeting.objects.get(meeting_id=meeting_id)
        
#         # Check if user is host or co-host
#         participant = Participant.objects.get(
#             meeting=meeting,
#             user=request.user,
#             role__in=['host', 'co_host'],
#             left_at__isnull=True
#         )
        
#         pending_requests = meeting.join_requests.filter(status='pending')
        
#         return Response({
#             'requests': JoinRequestSerializer(pending_requests, many=True).data
#         }, status=status.HTTP_200_OK)
        
#     except Meeting.DoesNotExist:
#         return Response({
#             'error': 'Meeting not found'
#         }, status=status.HTTP_404_NOT_FOUND)
    
#     except Participant.DoesNotExist:
#         return Response({
#             'error': 'Only host or co-host can view join requests'
#         }, status=status.HTTP_403_FORBIDDEN)


# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def send_invites(request, meeting_id):
#     """Send invites to additional participants"""
#     serializer = SendInviteSerializer(data=request.data)
    
#     if not serializer.is_valid():
#         return Response(
#             {'errors': serializer.errors},
#             status=status.HTTP_400_BAD_REQUEST
#         )
    
#     try:
#         meeting = Meeting.objects.get(meeting_id=meeting_id)
        
#         # Check if user is host or co-host
#         participant = Participant.objects.get(
#             meeting=meeting,
#             user=request.user,
#             role__in=['host', 'co_host'],
#             left_at__isnull=True
#         )
        
#         emails = serializer.validated_data['emails']
#         created_invites = []
        
#         for email in emails:
#             invite, created = MeetingInvite.objects.get_or_create(
#                 meeting=meeting,
#                 email=email,
#                 defaults={'invited_by': request.user}
#             )
            
#             if created:
#                 # Try to link to existing user
#                 try:
#                     user = User.objects.get(email=email)
#                     invite.user = user
#                     invite.save()
#                 except User.DoesNotExist:
#                     pass
                
#                 created_invites.append(invite)
                
#                 # Send email invitation (implement as needed)
#                 send_meeting_invitation(invite)
        
#         return Response({
#             'message': f'Sent {len(created_invites)} new invitations',
#             'invites': MeetingInviteSerializer(created_invites, many=True).data
#         }, status=status.HTTP_200_OK)
        
#     except Meeting.DoesNotExist:
#         return Response({
#             'error': 'Meeting not found'
#         }, status=status.HTTP_404_NOT_FOUND)
    
#     except Participant.DoesNotExist:
#         return Response({
#             'error': 'Only host or co-host can send invites'
#         }, status=status.HTTP_403_FORBIDDEN)

@swagger_auto_schema(
    method='post',
    operation_summary="Leave a meeting",
    tags=["Meetings"],
    manual_parameters=[
        openapi.Parameter(
            'meeting_id',
            openapi.IN_PATH,
            description="UUID of the meeting",
            type=openapi.TYPE_STRING,
            format=openapi.FORMAT_UUID,
            required=True
        )
    ],
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'guest_name': openapi.Schema(type=openapi.TYPE_STRING, description="Guest user's name if not logged in")
        }
    )
)
# Keep existing views with minor modifications
@api_view(['POST'])
@permission_classes([])
def leave_meeting(request, meeting_id):
    """Leave a meeting"""
    guest_name = request.data.get('guest_name', None)
    user = request.user if request.user.is_authenticated else None
    
    try:
        participant = Participant.objects.get(
            meeting__meeting_id=meeting_id,
            user=user,
            left_at__isnull=True
        )
        
        participant.leave_meeting()
        
        # Notify other participants
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f'meeting_{meeting_id}',
                {
                    'type': 'participant_left',
                    'participant_id': participant.id,
                    'user': user.username if user else guest_name
                }
            )
        
        return Response({
            'message': 'Successfully left meeting'
        }, status=status.HTTP_200_OK)
        
    except Participant.DoesNotExist:
        return Response({
            'error': 'You are not in this meeting'
        }, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(
    method='post',
    operation_summary="End a meeting (only host or co-host)",
    tags=["Meetings"],
    manual_parameters=[
        openapi.Parameter(
            'meeting_id',
            openapi.IN_PATH,
            description="UUID of the meeting",
            type=openapi.TYPE_STRING,
            format=openapi.FORMAT_UUID,
            required=True
        )
    ]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def end_meeting(request, meeting_id):
    """End a meeting (only host can do this)"""
    try:
        participant = Participant.objects.get(
            meeting__meeting_id=meeting_id,
            user=request.user,
            role__in=['host', 'co_host'],
            left_at__isnull=True
        )
        
        meeting = participant.meeting
        meeting.end_meeting()
        
        # Notify all participants
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f'meeting_{meeting_id}',
                {
                    'type': 'meeting_ended',
                    'ended_by': request.user.username,
                    'message': 'Meeting has been ended by host'
                }
            )
        
        return Response({
            'message': 'Meeting ended successfully'
        }, status=status.HTTP_200_OK)
        
    except Participant.DoesNotExist:
        return Response({
            'error': 'Only host or co-host can end meeting'
        }, status=status.HTTP_403_FORBIDDEN)




@swagger_auto_schema(
    method='get',
    operation_summary="Get live class details",
    operation_description="Retrieve details of a specific live class belonging to the authenticated teacher.",
    manual_parameters=[
        openapi.Parameter(
            'meeting_id',
            openapi.IN_PATH,
            description="UUID of the live class",
            type=openapi.TYPE_INTEGER
           
        )
    ],
    security=[{'Bearer': []}]
)

@swagger_auto_schema(
    method='delete',
    operation_summary="Cancel a live class",
    operation_description="Cancel a specific live class belonging to the authenticated teacher.",
    manual_parameters=[
        openapi.Parameter(
            'meeting_id',
            openapi.IN_PATH,
            description="UUID of the live class",
            type=openapi.TYPE_INTEGER
        
        )
    ],
 security=[{'Bearer': []}]
)
@api_view(['GET', 'DELETE'])
@permission_classes([AllowAny])
def meting_detail(request, meeting_id):
    """
    Get, update or delete specific live class
    """
    
    
    try:
        # teacher = TeacherProfile.objects.get(user=request.user)

        live_class = Meeting.objects.get(
            id=meeting_id, 
        )
   
    except Meeting.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Meeting class not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        serializer = MeetingSerializer(live_class,context={"request":request})
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    
    # elif request.method == 'PUT':
    #     # Update live class details
    #     allowed_fields = ['title', 'scheduled_time', 'max_participants', 'is_recorded']
    #     for field in allowed_fields:
    #         if field in request.data:
    #             setattr(live_class, field, request.data[field])
        
    #     live_class.save()
        
      
    #     serializer = LiveClassSerializer(live_class)
    #     return Response({
    #         'success': True,
    #         'message': 'Live class updated successfully',
    #         'data': serializer.data
    #     }, status=status.HTTP_200_OK)
    
    elif request.method == 'DELETE':
        if live_class.status == 'active':
            return Response({
                'success': False,
                'message': 'Cannot delete active live class'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        live_class.delete()
        return Response({
            'success': True,
            'message': 'Meeting deleted successfully'
        }, status=status.HTTP_200_OK)
    

    

@swagger_auto_schema(
    method='get',
    operation_summary="Get list of participants in a meeting",
    tags=["Meetings"],
    manual_parameters=[
        openapi.Parameter(
            'meeting_id',
            openapi.IN_PATH,
            description="UUID of the meeting",
            type=openapi.TYPE_STRING,
            format=openapi.FORMAT_UUID,
            required=True
        )
    ]
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_meeting_participants(request, meeting_id):
    """Get list of all participants in meeting"""
    try:
        meeting = Meeting.objects.get(meeting_id=meeting_id)
        
        # Check if user is in meeting
        user_participant = meeting.participants.filter(
            user=request.user,
            left_at__isnull=True
        ).first()
        
        if not user_participant:
            return Response({
                'error': 'You are not in this meeting'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get all active participants
        participants = meeting.participants.filter(left_at__isnull=True)
        
        return Response({
            'participants': ParticipantSerializer(participants, many=True).data
        }, status=status.HTTP_200_OK)
        
    except Meeting.DoesNotExist:
        return Response({
            'error': 'Meeting not found'
        }, status=status.HTTP_404_NOT_FOUND)


# @api_view(['GET'])
# @permission_classes([])
# def check_join_request_status(request, meeting_id, request_id):
#     """Check status of join request (for polling)"""
#     try:
#         join_request = JoinRequest.objects.get(
#             id=request_id,
#             meeting__meeting_id=meeting_id
#         )
        
#         return Response({
#             'status': join_request.status,
#             'request': JoinRequestSerializer(join_request).data
#         }, status=status.HTTP_200_OK)
        
#     except JoinRequest.DoesNotExist:
#         return Response({
#             'error': 'Join request not found'
#         }, status=status.HTTP_404_NOT_FOUND)


# Helper functions
def notify_host_about_join_request(meeting, join_request):
    """Notify host about new join request via WebSocket"""
    channel_layer = get_channel_layer()
    if channel_layer:
        async_to_sync(channel_layer.group_send)(
            f'meeting_{meeting.meeting_id}_host',
            {
                'type': 'join_request_received',
                'request': {
                    'id': join_request.id,
                    'name': join_request.guest_name or (join_request.user.get_full_name() if join_request.user else ''),
                    'email': join_request.guest_email,
                    'requested_at': join_request.requested_at.isoformat()
                }
            }
        )


def notify_join_request_response(join_request, response):
    """Notify requester about join request response"""
    channel_layer = get_channel_layer()
    if channel_layer:
        async_to_sync(channel_layer.group_send)(
            f'join_request_{join_request.id}',
            {
                'type': 'join_request_response',
                'status': response,
                'message': f'Your join request was {response}'
            }
        )


def notify_participant_joined(meeting_id, participant, user):
    """Notify other participants about new participant"""
    channel_layer = get_channel_layer()
    if channel_layer:
        async_to_sync(channel_layer.group_send)(
            f'meeting_{meeting_id}',
            {
                'type': 'participant_joined',
                'participant': {
                    'id': participant.id,
                    'user': user.username,
                    'guest_name': participant.guest_name,
                    'role': participant.role,
                    'joined_at': participant.joined_at.isoformat()
                }
            }
        )


def send_meeting_invitation(invite):

    """Send email invitation (implement based on your email service)"""
    try:
        subject = f'You are invited to join "{invite.meeting.title}"'
        message = f"""
        Hello,
        
        You have been invited to join a meeting:
        
        Meeting: {invite.meeting.title}
        Host: {invite.meeting.host.get_full_name() or invite.meeting.host.username}
        
        Join URL: http://127.0.0.1:8000/api/meeting/join/{invite.meeting.meeting_id}
        Password: {invite.meeting.password if invite.meeting.password else 'No password required'}
        
        Best regards,
        Meeting Team
        """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [invite.email],
            fail_silently=True,
        )
    except Exception as e:
        print(f"Failed to send email invitation: {e}")