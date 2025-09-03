# admin_dashboard/views.py

from rest_framework import status, permissions, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404
from django.db import models
from notifications.models import Notification
from authentication.models import User,TeacherProfile,StudentProfile, StudentQuery
from authentication.serializers import UserSerializer,StudentQuerySerializer,StudentQueryListSerializer
from courses.models import Course, Teacher, Enrollment
from courses.serializers import CourseListSerializer
from payments.models import Payment
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import uuid

@swagger_auto_schema(
    method='get',
    operation_summary="Admin Dashboard Overview",
    operation_description="Get an overview of statistics for admin dashboard, including users, courses, payments, and recent activities.",
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_dashboard_overview(request):
    """
    Admin dashboard overview with statistics
    """
    # Check if user is admin
    if request.user.role != 'admin':
        return Response({
            'success': False,
            'message': 'Access denied. Admin privileges required.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Get statistics
    total_users = User.objects.count()
    total_students = User.objects.filter(role='student').count()
    total_teachers = User.objects.filter(role='teacher').count()
    total_admins = User.objects.filter(role='admin').count()
    total_subadmins = User.objects.filter(role='subadmin').count()
    
    # Course statistics
    total_courses = Course.objects.count()
    active_courses = Course.objects.filter(is_active=True).count()
    paid_courses = Course.objects.filter(course_type='paid').count()
    free_courses = Course.objects.filter(course_type='free').count()
    
    # Payment statistics
    total_payments = Payment.objects.count()
    successful_payments = Payment.objects.filter(is_successful=True).count()
    total_revenue = Payment.objects.filter(is_successful=True).aggregate(
        total=Sum('amount')
    )['total'] or 0
    
    # Recent activity
    recent_users = User.objects.order_by('-created_at')[:5]
    recent_courses = Course.objects.order_by('-created_at')[:5]
    recent_payments = Payment.objects.filter(is_successful=True).order_by('-created_at')[:5]
    
    return Response({
        'success': True,
        'data': {
            'user_statistics': {
                'total_users': total_users,
                'total_students': total_students,
                'total_teachers': total_teachers,
                'total_admins': total_admins,
                'total_subadmins': total_subadmins
            },
            'course_statistics': {
                'total_courses': total_courses,
                'active_courses': active_courses,
                'paid_courses': paid_courses,
                'free_courses': free_courses
            },
            'payment_statistics': {
                'total_payments': total_payments,
                'successful_payments': successful_payments,
                'total_revenue': float(total_revenue)
            },
            'recent_activity': {
                'recent_users': UserSerializer(recent_users, many=True).data,
                'recent_courses': CourseListSerializer(recent_courses, many=True,context = {'request':request}).data,
                'recent_payments': [
                    {
                        'id': payment.id,
                        'user': payment.user.username,
                        'amount': float(payment.amount),
                        'gateway': payment.gateway,
                        'created_at': payment.created_at
                    } for payment in recent_payments
                ]
            }
        }
    }, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='get',
    operation_summary="List Users (Admin/Subadmin)",
    manual_parameters=[
        openapi.Parameter('role', openapi.IN_QUERY, description="Filter by role (student, teacher, admin, subadmin)", type=openapi.TYPE_STRING),
        openapi.Parameter('search', openapi.IN_QUERY, description="Search by username, email, first_name, last_name", type=openapi.TYPE_STRING),
        openapi.Parameter('is_verified', openapi.IN_QUERY, description="Filter by verification status (true/false)", type=openapi.TYPE_BOOLEAN),
    ],
    responses={200: "List of users"}
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_users_list(request):
    """
    Get all users with filtering and role information
    """
    if request.user.role not in ['admin', 'subadmin']:
        return Response({
            'success': False,
            'message': 'Access denied. Admin privileges required.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Get query parameters
    role_filter = request.query_params.get('role', None)
    search = request.query_params.get('search', None)
    is_verified = request.query_params.get('is_verified', None)
    
    # Base queryset
    users = User.objects.all().order_by('-created_at')
    
    # Apply filters
    if role_filter:
        users = users.filter(role=role_filter)
    
    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    
    if is_verified is not None:
        users = users.filter(is_verified=is_verified.lower() == 'true')
    
    # Serialize users
    serializer = UserSerializer(users, many=True)
    
    return Response({
        'success': True,
        'data': {
            'total_users': users.count(),
            'users': serializer.data
        }
    }, status=status.HTTP_200_OK)

# ========================
# Approve/reject Teacher Profile
# ==================================
@swagger_auto_schema(
    method='put',
    operation_summary="Review Teacher/Student Profile (Admin only)",
    manual_parameters=[
        openapi.Parameter('profile_type', openapi.IN_QUERY, description="Type of profile (student/teacher)", type=openapi.TYPE_STRING),
        openapi.Parameter('profile_id', openapi.IN_QUERY, description="Profile ID to review", type=openapi.TYPE_STRING,format='uuid')
    ],
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'action': openapi.Schema(type=openapi.TYPE_STRING, description="approve or reject")
        },
        required=['action']
    ),
    responses={200: "Profile reviewed successfully"}
)
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def admin_review_profile(request):
    """Approve or reject teacher/student profiles (Admin only)"""
    if request.user.role != 'admin':
        return Response({
            'success': False,
            'message': 'Access denied. Admin privileges required.'
        }, status=status.HTTP_403_FORBIDDEN)

    profile_type = request.query_params.get('profile_type')
    profile_id = request.query_params.get('profile_id')
    action = request.data.get('action')

    if profile_type not in ['student', 'teacher']:
        return Response({'success': False, 'message': 'Invalid profile type'}, status=400)
    if action not in ['approve', 'reject']:
        return Response({'success': False, 'message': 'Invalid action'}, status=400)

    
    try:
        profile_uuid = uuid.UUID(profile_id)
        user_obj = User.objects.get(id=profile_uuid)
    except User.DoesNotExist:
        return Response({'success': False, 'message': 'Profile not found'}, status=404)

     # Update status on the actual profile model
    if profile_type == 'student':
        profile = StudentProfile.objects.get(user=user_obj)
    else:
        profile = TeacherProfile.objects.get(user=user_obj)
    # Update status
    profile.status = 'approved' if action == 'approve' else 'rejected'
    profile.save()

    # Also update user role if approved
    if action == 'approve':
        user_obj.role = profile_type
        user_obj.save()

    # Send notification to the user
    Notification.objects.create(
        recipient=profile.user,
        sender=request.user,
        notification_type='general',
        title=f"Your {profile_type} profile has been {profile.status}",
        message=f"Admin has {profile.status} your {profile_type} profile."
    )

    return Response({
        'success': True,
        'message': f'{profile_type.title()} profile {profile.status} successfully'
    }, status=200)

@swagger_auto_schema(
    method='get',
    operation_summary="Get pending teacher or student profiles (Admin only)",
    # manual_parameters=[
    #     openapi.Parameter('profile_type', openapi.IN_QUERY, description="Type of profile (student/teacher)", type=openapi.TYPE_STRING)
    # ],
    responses={200: "List of pending profiles"}
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_pending_profiles_list(request):
    """
    Get all pending teacher or student profiles (Admin only)
    """
    if request.user.role not in ['admin', 'subadmin']:
        return Response({
            'success': False,
            'message': 'Access denied. Admin privileges required.'
        }, status=status.HTTP_403_FORBIDDEN)

    # profile_type = request.query_params.get('profile_type')

    # if profile_type not in ['student', 'teacher']:
    #     return Response({
    #         'success': False,
    #         'message': "Invalid or missing profile_type. Use 'student' or 'teacher'."
    #     }, status=status.HTTP_400_BAD_REQUEST)

    # model = StudentProfile if profile_type == 'student' else TeacherProfile
    model = TeacherProfile
    profiles = model.objects.filter(status='pending').select_related('user')

    data = []
    for profile in profiles:
        user_data = UserSerializer(profile.user).data
        data.append({
            'profile_id': profile.id,
            'user': user_data,
            'status': profile.status,
            'created_at': profile.created_at if hasattr(profile, 'created_at') else None
        })

    return Response({
        'success': True,
        'total_pending': len(data),
        'profiles': data
    }, status=status.HTTP_200_OK)

@swagger_auto_schema(
    method='put',
    operation_summary="Update User Role (Admin only)",
    manual_parameters=[
        openapi.Parameter('user_id', openapi.IN_PATH, description="User ID to update", type=openapi.TYPE_STRING)
    ],
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'role': openapi.Schema(type=openapi.TYPE_STRING, description="New role (student, teacher, admin, subadmin)")
        },
        required=['role']
    ),
    responses={200: "Role updated successfully"}
)
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def admin_update_user_role(request, user_id):
    """
    Update user role (Admin only)
    """
    if request.user.role != 'admin':
        return Response({
            'success': False,
            'message': 'Access denied. Admin privileges required.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        user = User.objects.get(id=user_id)
        new_role = request.data.get('role')
        
        if new_role not in ['student', 'teacher', 'admin', 'subadmin']:
            return Response({
                'success': False,
                'message': 'Invalid role specified'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user.role = new_role
        user.save()
        
        return Response({
            'success': True,
            'message': f'User role updated to {new_role}',
            'data': UserSerializer(user).data
        }, status=status.HTTP_200_OK)
        
    except User.DoesNotExist:
        return Response({
            'success': False,
            'message': 'User not found'
        }, status=status.HTTP_404_NOT_FOUND)


@swagger_auto_schema(
    method='get',
    operation_summary="Get all teachers with their courses",
    operation_description="Returns a list of all teachers with their basic info and course statistics.",
    responses={
        200: openapi.Response(
            description="Successful Response",)
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_teachers_courses(request):
    """
    Get all teachers with their courses
    """
    if request.user.role not in ['admin', 'subadmin']:
        return Response({
            'success': False,
            'message': 'Access denied. Admin privileges required.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Get all teachers
    teachers = TeacherProfile.objects.select_related('user').prefetch_related('course_set')
    
    teachers_data = []
    for teacher in teachers:
        courses = Course.objects.filter(teacher=teacher)
        teacher_info = {
            'id': teacher.id,
            'user_id': teacher.user.id,
            'username': teacher.user.username,
            'email': teacher.user.email,
            'bio': teacher.bio,
            'is_verified': teacher.user.is_verified,
            'created_at': teacher.user.created_at,
            'courses': {
                'total_courses': courses.count(),
                'active_courses': courses.filter(is_active=True).count(),
                'paid_courses': courses.filter(course_type='paid').count(),
                'free_courses': courses.filter(course_type='free').count(),
                'course_list': CourseListSerializer(courses, many=True, context={'request': request}).data
            }
        }
        teachers_data.append(teacher_info)
    
    return Response({
        'success': True,
        'data': {
            'total_teachers': len(teachers_data),
            'teachers': teachers_data
        }
    }, status=status.HTTP_200_OK)


# ===========================
# Admin Payment
# ===========================
@swagger_auto_schema(
    method='get',
    tags=['Admin - Payments'],
    operation_summary="Get all course payments",
    operation_description="Returns payment records with optional filtering by course, status, and gateway.",
    manual_parameters=[
        openapi.Parameter('course_id', openapi.IN_QUERY, description="Filter by course ID", type=openapi.TYPE_INTEGER),
        openapi.Parameter('status', openapi.IN_QUERY, description="Filter by payment status (successful/failed)", type=openapi.TYPE_STRING),
        openapi.Parameter('gateway', openapi.IN_QUERY, description="Filter by payment gateway name", type=openapi.TYPE_STRING),
    ]
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_course_payments(request):
    """
    Get all course payments with student and course details
    """
    if request.user.role not in ['admin', 'subadmin']:
        return Response({
            'success': False,
            'message': 'Access denied. Admin privileges required.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Get query parameters
    course_id = request.query_params.get('course_id', None)
    payment_status = request.query_params.get('status', None)
    gateway = request.query_params.get('gateway', None)
    
    # Base queryset
    payments = Payment.objects.select_related('user', 'course').order_by('-created_at')
    
    # Apply filters
    if course_id:
        payments = payments.filter(course__id=course_id)
    
    if payment_status:
        is_successful = payment_status.lower() == 'successful'
        payments = payments.filter(is_successful=is_successful)
    
    if gateway:
        payments = payments.filter(gateway=gateway)
    
    # Serialize payments
    payment_data = []
    for payment in payments:
        payment_info = {
            'id': payment.id,
            'transaction_ref': payment.txn_ref,
            'amount': float(payment.amount),
            'gateway': payment.gateway,
            'is_successful': payment.is_successful,
            'created_at': payment.created_at,
            'student': {
                'id': payment.user.id,
                'username': payment.user.username,
                'email': payment.user.email
            },
            'course': {
                'id': payment.meeting.id,
                'title': getattr(payment.meeting, 'title', 'N/A')
            }
        }
        payment_data.append(payment_info)
    
    # Payment summary
    total_amount = sum(p.amount for p in payments if p.is_successful)
    successful_count = payments.filter(is_successful=True).count()
    failed_count = payments.filter(is_successful=False).count()
    
    return Response({
        'success': True,
        'data': {
            'summary': {
                'total_payments': payments.count(),
                'successful_payments': successful_count,
                'failed_payments': failed_count,
                'total_revenue': float(total_amount)
            },
            'payments': payment_data
        }
    }, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='put',
    tags=['Admin - Payments'],
    operation_summary="Verify or update payment status",
    manual_parameters=[
        openapi.Parameter('payment_id', openapi.IN_PATH, description="ID of the payment to update", type=openapi.TYPE_STRING)
    ],
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'is_successful': openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Set True if payment is successful")
        }
    )
)
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def admin_verify_payment(request, payment_id):
    """
    Verify/Update payment status (Admin only)
    """
    if request.user.role != 'admin':
        return Response({
            'success': False,
            'message': 'Access denied. Admin privileges required.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        payment = Payment.objects.get(id=payment_id)
        is_successful = request.data.get('is_successful', payment.is_successful)
        
        payment.is_successful = is_successful
        payment.save()
        
        return Response({
            'success': True,
            'message': f'Payment {"verified" if is_successful else "marked as failed"}',
            'data': {
                'payment_id': payment.id,
                'is_successful': payment.is_successful,
                'amount': float(payment.amount)
            }
        }, status=status.HTTP_200_OK)
        
    except Payment.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Payment not found'
        }, status=status.HTTP_404_NOT_FOUND)



@swagger_auto_schema(
    method='get',
    operation_summary=" Get all course enrollments with student details",
    operation_description="Returns Course",
    manual_parameters=[
        openapi.Parameter('course_id', openapi.IN_QUERY, description="Filter by course ID", type=openapi.TYPE_INTEGER),
        openapi.Parameter('course_type', openapi.IN_QUERY, description="Filter by Course Type (paid/unpaid)", type=openapi.TYPE_STRING),
        openapi.Parameter('is_completed', openapi.IN_QUERY, description="Filter by complete or not", type=openapi.TYPE_STRING),
    ]
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_course_enrollments(request):
    """
    Get all course enrollments with student details
    """
    if request.user.role not in ['admin', 'subadmin']:
        return Response({
            'success': False,
            'message': 'Access denied. Admin privileges required.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Get query parameters
    course_id = request.query_params.get('course_id', None)
    
    # Base queryset
    enrollments = Enrollment.objects.select_related('course').order_by('-enrolled_at')
    
    if course_id:
        enrollments = enrollments.filter(course_id=course_id)
    
    # Serialize enrollments
    enrollment_data = []
    for enrollment in enrollments:
        enrollment_info = {
            'id': enrollment.id,
            'enrolled_at': enrollment.enrolled_at,
            'is_completed': enrollment.is_completed,
            'course': {
                'id': enrollment.course.id,
                'title': enrollment.course.title,
                'course_type': enrollment.course.course_type,
                'price': float(enrollment.course.price)
            }
        }
        enrollment_data.append(enrollment_info)
    
    return Response({
        'success': True,
        'data': {
            'total_enrollments': enrollments.count(),
            'enrollments': enrollment_data
        }
    }, status=status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def admin_delete_user(request, user_id):
    """
    Delete user (Admin only)
    """
    if request.user.role != 'admin':
        return Response({
            'success': False,
            'message': 'Access denied. Admin privileges required.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        user = User.objects.get(id=user_id)
        
        # Prevent admin from deleting themselves
        if user.id == request.user.id:
            return Response({
                'success': False,
                'message': 'Cannot delete your own account'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        username = user.username
        user.delete()
        
        return Response({
            'success': True,
            'message': f'User {username} deleted successfully'
        }, status=status.HTTP_200_OK)
        
    except User.DoesNotExist:
        return Response({
            'success': False,
            'message': 'User not found'
        }, status=status.HTTP_404_NOT_FOUND)

@swagger_auto_schema(
    method='get',
    operation_summary="  Get detailed information about a specific users",
    operation_description="Returns User",
     manual_parameters=[
        openapi.Parameter('user_id', openapi.IN_PATH, description="User ID to update", type=openapi.TYPE_STRING)
    ],
  
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_user_detail(request, user_id):
    """
    Get detailed information about a specific user
    """
    if request.user.role not in ['admin', 'subadmin']:
        return Response({
            'success': False,
            'message': 'Access denied. Admin privileges required.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        user = User.objects.get(id=user_id)
        
        # Get user's additional information based on role
        additional_info = {}
        
        if user.role == 'teacher':
            try:
                teacher = TeacherProfile.objects.get(user=user)
                courses = Course.objects.filter(teacher=teacher)
                additional_info = {
                    'teacher_profile': {
                        'bio': teacher.bio,
                        'total_courses': courses.count(),
                        'active_courses': courses.filter(is_active=True).count()
                    }
                }
            except TeacherProfile.DoesNotExist:
                additional_info = {'teacher_profile': None}
        
        elif user.role == 'student':
            enrollments = Enrollment.objects.filter(course__in=Course.objects.all())
            payments = Payment.objects.filter(user=user)
            additional_info = {
                'student_profile': {
                    'total_enrollments': enrollments.count(),
                    'completed_courses': enrollments.filter(is_completed=True).count(),
                    'total_payments': payments.filter(is_successful=True).count(),
                    'total_spent': float(payments.filter(is_successful=True).aggregate(
                        total=Sum('amount'))['total'] or 0)
                }
            }
        
        user_data = UserSerializer(user).data
        user_data.update(additional_info)
        
        return Response({
            'success': True,
            'data': user_data
        }, status=status.HTTP_200_OK)
        
    except User.DoesNotExist:
        return Response({
            'success': False,
            'message': 'User not found'
        }, status=status.HTTP_404_NOT_FOUND)
    







# support_feedback/views.py
from support_feedback.models import SupportTicket, CourseFeedback, TeacherFeedback
from support_feedback.serializers import (
    SupportTicketSerializer,
    CourseFeedbackSerializer, TeacherFeedbackSerializer,
     TicketReplyCreateSerializer
)
    
# Admin Views (for admin dashboard app)
class AdminSupportTicketListView(generics.ListAPIView):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = SupportTicketSerializer
    queryset = SupportTicket.objects.all()

class AdminSupportTicketDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAdminUser] 
    serializer_class = SupportTicketSerializer
    queryset = SupportTicket.objects.all()

    @swagger_auto_schema(
        tags=['Admin Support Ticket'],
        operation_summary="Retrieve a support ticket",
        operation_description="Get details of a specific support ticket by ID. Admin access only.",
        responses={200: SupportTicketSerializer()}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Admin Support Ticket'],
        operation_summary="Update a support ticket",
        operation_description="Update fields of a specific support ticket. Admin access only.",
        request_body=SupportTicketSerializer,
        responses={200: SupportTicketSerializer()}
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)


@swagger_auto_schema(
    method='post',
    tags=[
        'Admin Support Ticket'
    ],
    operation_summary="Reply to a ticket (Admin only)",
    operation_description="Admin can reply to a support ticket by providing a message.",
    request_body=TicketReplyCreateSerializer,
    responses={
        201: TicketReplyCreateSerializer,
        400: "Bad Request - Validation errors"
    },
    manual_parameters=[
        openapi.Parameter(
            'ticket_id',
            openapi.IN_PATH,
            description="ID of the support ticket",
            type=openapi.TYPE_STRING
        )
    ]
)
@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])
def admin_reply_ticket(request, ticket_id):
    ticket = get_object_or_404(SupportTicket, id=ticket_id)
    serializer = TicketReplyCreateSerializer(data=request.data)
    
    if serializer.is_valid():
        serializer.save(ticket=ticket, user=request.user, is_admin_reply=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AdminCourseFeedbackListView(generics.ListAPIView):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = CourseFeedbackSerializer
    queryset = CourseFeedback.objects.all()

    @swagger_auto_schema(
        tags=['Admin Support Ticket'],
        operation_summary="List all course feedback",
        operation_description="Retrieve all course feedback entries. Admin access only.",
        responses={200: CourseFeedbackSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

class AdminTeacherFeedbackListView(generics.ListAPIView):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = TeacherFeedbackSerializer  
    queryset = TeacherFeedback.objects.all()

    @swagger_auto_schema(
        tags=['Admin Support Ticket'],
        operation_summary="List all teacher feedback",
        operation_description="Retrieve all teacher feedback entries. Admin access only.",
        responses={200: TeacherFeedbackSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    


class AdminStudentQueriesView(APIView):
    """
    Admin view to manage student queries
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get all student queries"""
        queries = StudentQuery.objects.all()
        
        # Filter options
        status_filter = request.query_params.get('status')
        if status_filter == 'pending':
            queries = queries.filter(is_processed=False)
        elif status_filter == 'processed':
            queries = queries.filter(is_processed=True)
        elif status_filter == 'registered':
            queries = queries.filter(is_registered=True)
        
        serializer = StudentQueryListSerializer(queries, many=True)
        return Response({
            'success': True,
            'data': serializer.data,
            'count': queries.count()
        })
    
    def patch(self, request, query_id):
        """Update query status"""
        try:
            query = StudentQuery.objects.get(id=query_id)
            query.is_processed = request.data.get('is_processed', query.is_processed)
            query.admin_notes = request.data.get('admin_notes', query.admin_notes)
            query.save()
            
            serializer = StudentQueryListSerializer(query)
            return Response({
                'success': True,
                'message': 'Query updated successfully',
                'data': serializer.data
            })
        except StudentQuery.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Query not found'
            }, status=status.HTTP_404_NOT_FOUND)

