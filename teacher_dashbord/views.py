# teacher_dashboard/views.py

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db import transaction
from authentication.models import TeacherProfile
from courses.models import Course, Video, Quiz, Assignment, Enrollment, Topic
from courses.serializers import CourseListSerializer, VideoDetailSerializer, QuizSerializer, AssignmentSerializer 
from .serializers import TeacherCourseSerializer, TeacherVideoSerializer, TeacherQuizSerializer, EnrolledStudentSerializer,LiveClassSerializer, TeacherAssignmentSerializer,TeacherTopicSerializer
from meetings.models import Meeting
from django.core.mail import send_mail
from datetime import datetime
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .permissions import IsTeacher

@swagger_auto_schema(
    method='get',
    operation_summary="Get teacher dashboard statistics",
    operation_description="Returns overview statistics for teacher dashboard including course counts, student counts, and recent courses.",
    responses={
        200: openapi.Response(
            description="Dashboard data retrieved successfully",
        ),
        403: openapi.Response(
            description="Forbidden - Teacher privileges required",
                   ),
        404: openapi.Response(
            description="Teacher profile not found",
                 )
    },
    security=[{'Bearer': []}]
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teacher_dashboard(request):
    """
    Teacher dashboard overview
    """
    # Check if user is teacher
    if request.user.role != 'teacher':
        return Response({
            'success': False,
            'message': 'Access denied. Teacher privileges required.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        teacher = TeacherProfile.objects.get(user=request.user)
    except TeacherProfile.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Teacher profile not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Get teacher's courses statistics
    courses = Course.objects.filter(teacher=teacher)
    total_courses = courses.count()
    active_courses = courses.filter(is_active=True).count()
    total_students = Enrollment.objects.filter(course__teacher=teacher).count()
    total_videos = Video.objects.filter(course__teacher=teacher).count()
    total_quizzes = Quiz.objects.filter(course__teacher=teacher).count()
    total_live_classes = Meeting.objects.filter(course__teacher=teacher, meeting_type='lecture').count()
    
    # Recent courses
    recent_courses = courses.order_by('-created_at')[:5]
    
    return Response({
        'success': True,
        'data': {
            'profile_picture': teacher.profile_picture.url if teacher.profile_picture else None,
            'teacher_name': teacher.user.username,
            'teacher_bio': teacher.bio,
            'statistics': {
                'total_courses': total_courses,
                'active_courses': active_courses,
                'total_students': total_students,
                'total_videos': total_videos,
                'total_quizzes': total_quizzes,
                'total_live_classes': total_live_classes,
            },
            'recent_courses': CourseListSerializer(recent_courses, many=True).data
        }
    }, status=status.HTTP_200_OK)

#=========================================
# Teacher's courses
# ========================================
@swagger_auto_schema(
    method='get',
    tags=["Teacher's Course"],
    operation_summary="List all teacher's courses",
    operation_description="Retrieve a list of all courses belonging to the authenticated teacher.",
    responses={
        200: openapi.Response(
            description="Courses retrieved successfully",
            schema=TeacherCourseSerializer(many=True)
        ),
        403: openapi.Response(
            description="Forbidden - Teacher privileges required",
         
        ),
        404: openapi.Response(
            description="Teacher profile not found",
           
        )
    },
    security=[{'Bearer': []}]
)
@swagger_auto_schema(
    method='post',
     tags=["Teacher's Course"],
    operation_summary="Create a new course",
    operation_description="Create a new course for the authenticated teacher.",
    request_body=TeacherCourseSerializer,
    responses={
        201: openapi.Response(
            description="Course created successfully",
            schema=TeacherCourseSerializer
        ),
        400: openapi.Response(
            description="Bad request - Invalid data",
          
        ),
        403: openapi.Response(
            description="Forbidden - Teacher privileges required",
            
        ),
        404: openapi.Response(
            description="Teacher profile not found",
           
        )
    },
    security=[{'Bearer': []}]
)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def teacher_courses(request):
    """
    Get teacher's courses or create new course
    """
    print(request.user.id, request.user.username)
    print(TeacherProfile.objects.values_list("user_id", "full_name"))
    if request.user.role != 'teacher':
        return Response({
            'success': False,
            'message': 'Access denied. Teacher privileges required.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        teacher = TeacherProfile.objects.get(user=request.user)
    except TeacherProfile.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Teacher profile not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        courses = Course.objects.filter(teacher=teacher).order_by('-created_at')
        serializer = TeacherCourseSerializer(courses, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    
    elif request.method == 'POST':
        serializer = TeacherCourseSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(teacher=teacher)
            return Response({
                'success': True,
                'message': 'Course created successfully',
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'message': 'Course creation failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)



@swagger_auto_schema(
    method='get',
     tags=["Teacher's Course"],
    operation_summary="Get course details",
    operation_description="Retrieve details of a specific course belonging to the authenticated teacher.",
    manual_parameters=[
        openapi.Parameter(
            'course_id',
            openapi.IN_PATH,
            description="UUID of the course",
            type=openapi.TYPE_STRING,
            format=openapi.FORMAT_UUID
        )
    ],
    responses={
        200: openapi.Response(
            description="Course details retrieved successfully",
            schema=TeacherCourseSerializer
        ),
        403: openapi.Response(
            description="Forbidden - Teacher privileges required",
            
        ),
        404: openapi.Response(
            description="Course or teacher profile not found",
          
        )
    },
    security=[{'Bearer': []}]
)
@swagger_auto_schema(
    method='put',
     tags=["Teacher's Course"],
    operation_summary="Update course details",
    operation_description="Update details of a specific course belonging to the authenticated teacher.",
    manual_parameters=[
        openapi.Parameter(
            'course_id',
            openapi.IN_PATH,
            description="UUID of the course",
            type=openapi.TYPE_STRING,
            format=openapi.FORMAT_UUID
        )
    ],
    request_body=TeacherCourseSerializer,
    responses={
        200: openapi.Response(
            description="Course updated successfully",
            schema=TeacherCourseSerializer
        ),
        400: openapi.Response(
            description="Bad request - Invalid data",
        ),
        403: openapi.Response(
            description="Forbidden - Teacher privileges required",
        ),
        404: openapi.Response(
            description="Course or teacher profile not found",
        )
    },
    security=[{'Bearer': []}]
)
@swagger_auto_schema(
    method='delete',
     tags=["Teacher's Course"],
    operation_summary="Delete a course",
    operation_description="Delete a specific course belonging to the authenticated teacher.",
    manual_parameters=[
        openapi.Parameter(
            'course_id',
            openapi.IN_PATH,
            description="UUID of the course",
            type=openapi.TYPE_STRING,
            format=openapi.FORMAT_UUID
        )
    ],
    responses={
        200: openapi.Response(
            description="Course deleted successfully",
          
        ),
        403: openapi.Response(
            description="Forbidden - Teacher privileges required",
          
        ),
        404: openapi.Response(
            description="Course or teacher profile not found",
           
        )
    },
    security=[{'Bearer': []}]
)
@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def teacher_course_detail(request, course_id):
    """
    Get, update or delete teacher's specific course
    """
    if request.user.role != 'teacher':
        return Response({
            'success': False,
            'message': 'Access denied. Teacher privileges required.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        teacher = TeacherProfile.objects.get(user=request.user)
        course = Course.objects.get(id=course_id, teacher=teacher)
    except TeacherProfile.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Teacher profile not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Course.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Course not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        serializer = TeacherCourseSerializer(course)
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    
    elif request.method == 'PUT':
        serializer = TeacherCourseSerializer(course, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Course updated successfully',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        
        return Response({
            'success': False,
            'message': 'Course update failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        course.delete()
        return Response({
            'success': True,
            'message': 'Course deleted successfully'
        }, status=status.HTTP_200_OK)


# ===========================
# Teacher Course Vedios
# ============================
@swagger_auto_schema(
    method='get',
     tags=["Teacher Course Vedio"],
    operation_summary="List course videos",
    operation_description="Retrieve all videos for a specific course belonging to the authenticated teacher.",
    manual_parameters=[
        openapi.Parameter(
            'course_id',
            openapi.IN_PATH,
            description="UUID of the course",
            type=openapi.TYPE_STRING,
            format=openapi.FORMAT_UUID
        )
    ],
       security=[{'Bearer': []}]
)
@swagger_auto_schema(
    method='post',
    tags=["Teacher Course Vedio"],
    operation_summary="Add video to course",
    operation_description="Add a new video to a specific course belonging to the authenticated teacher.",
    manual_parameters=[
        openapi.Parameter(
            'course_id',
            openapi.IN_PATH,
            description="UUID of the course",
            type=openapi.TYPE_STRING,
            format=openapi.FORMAT_UUID
        )
    ],
    request_body=TeacherVideoSerializer,
    
    security=[{'Bearer': []}]
)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def teacher_course_videos(request, course_id):
    """
    Get course videos or add new video to course
    """
    if request.user.role != 'teacher':
        return Response({
            'success': False,
            'message': 'Access denied. Teacher privileges required.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        teacher = TeacherProfile.objects.get(user=request.user)
        course = Course.objects.get(id=course_id, teacher=teacher)
    except TeacherProfile.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Teacher profile not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Course.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Course not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        videos = Video.objects.filter(course=course).order_by('order')
        serializer = TeacherVideoSerializer(videos, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    
    elif request.method == 'POST':
        serializer = TeacherVideoSerializer(data=request.data)
        if serializer.is_valid():
            topic_id = request.data.get('topic')
            if topic_id:
                try:
                    topic = Topic.objects.get(id=topic_id, course=course)
                    serializer.save(course=course, topic=topic)
                except Topic.DoesNotExist:
                    return Response({
                        'success': False,
                        'message': 'Topic not found or does not belong to this course'
                    }, status=status.HTTP_400_BAD_REQUEST)
            else:
                serializer.save(course=course)
            return Response({
                'success': True,
                'message': 'Video added successfully',
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'message': 'Video upload failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)



@swagger_auto_schema(
    method='get',
    tags=["Teacher Course Vedio"],
    operation_summary="Get video details",
    operation_description="Retrieve details of a specific video belonging to the authenticated teacher.",
    manual_parameters=[
        openapi.Parameter(
            'video_id',
            openapi.IN_PATH,
            description="UUID of the video",
            type=openapi.TYPE_STRING,
            format=openapi.FORMAT_UUID
        )
    ],
   security=[{'Bearer': []}]
)
@swagger_auto_schema(
    method='put',
    tags=["Teacher Course Vedio"],
    operation_summary="Update video details",
    operation_description="Update details of a specific video belonging to the authenticated teacher.",
    manual_parameters=[
        openapi.Parameter(
            'video_id',
            openapi.IN_PATH,
            description="UUID of the video",
            type=openapi.TYPE_STRING,
            format=openapi.FORMAT_UUID
        )
    ],
    request_body=TeacherVideoSerializer,
   security=[{'Bearer': []}]
)
@swagger_auto_schema(
    method='delete',
    tags=["Teacher Course Vedio"],
    operation_summary="Delete a video",
    operation_description="Delete a specific video belonging to the authenticated teacher.",
    manual_parameters=[
        openapi.Parameter(
            'video_id',
            openapi.IN_PATH,
            description="UUID of the video",
            type=openapi.TYPE_STRING,
            format=openapi.FORMAT_UUID
        )
    ],
     security=[{'Bearer': []}]
)
@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def teacher_video_detail(request, video_id):
    """
    Get, update or delete specific video
    """
    if request.user.role != 'teacher':
        return Response({
            'success': False,
            'message': 'Access denied. Teacher privileges required.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        teacher = TeacherProfile.objects.get(user=request.user)
        video = Video.objects.get(id=video_id, course__teacher=teacher)
    except TeacherProfile.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Teacher profile not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Video.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Video not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        serializer = TeacherVideoSerializer(video)
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    
    elif request.method == 'PUT':
        serializer = TeacherVideoSerializer(video, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Video updated successfully',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        
        return Response({
            'success': False,
            'message': 'Video update failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        video.delete()
        return Response({
            'success': True,
            'message': 'Video deleted successfully'
        }, status=status.HTTP_200_OK)


# Topic specific videos
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teacher_topic_videos(request, topic_id):
    """
    Get videos for a specific topic
    """
    if request.user.role != 'teacher':
        return Response({
            'success': False,
            'message': 'Access denied. Teacher privileges required.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        teacher = TeacherProfile.objects.get(user=request.user)
        topic = Topic.objects.get(id=topic_id, course__teacher=teacher, is_active=True)
    except TeacherProfile.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Teacher profile not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Topic.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Topic not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        videos = Video.objects.filter(topic=topic).order_by('order')
        serializer = TeacherVideoSerializer(videos, many=True)
        return Response({
            'success': True,
            'data': {
                'topic': topic.title,
                'videos': serializer.data
            }
        }, status=status.HTTP_200_OK)
    
# =================================
# Teacher Get Course student
# =================================


@swagger_auto_schema(
    method='get',
    operation_summary="List enrolled students",
    operation_description="Retrieve all enrolled students for a specific course belonging to the authenticated teacher.",
    manual_parameters=[
        openapi.Parameter(
            'course_id',
            openapi.IN_PATH,
            description="UUID of the course",
            type=openapi.TYPE_STRING,
            format=openapi.FORMAT_UUID
        )
    ],
     security=[{'Bearer': []}]
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teacher_course_students(request, course_id):
    """
    Get enrolled students for a specific course
    """
    if request.user.role != 'teacher':
        return Response({
            'success': False,
            'message': 'Access denied. Teacher privileges required.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        teacher = TeacherProfile.objects.get(user=request.user)
        course = Course.objects.get(id=course_id, teacher=teacher)
    except TeacherProfile.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Teacher profile not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Course.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Course not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    enrollments = Enrollment.objects.filter(course=course).order_by('-enrolled_at')
    serializer = EnrolledStudentSerializer(enrollments, many=True)
    
    return Response({
        'success': True,
        'data': {
            'course_title': course.title,
            'total_students': enrollments.count(),
            'students': serializer.data
        }
    }, status=status.HTTP_200_OK)


# ==================================
# Teacher course quize
# ==================================


@swagger_auto_schema(
    method='get',
    tags=["Teacher's Course Quize"],
    operation_summary="List course quizzes",
    operation_description="Retrieve all quizzes for a specific course belonging to the authenticated teacher.",
    manual_parameters=[
        openapi.Parameter(
            'course_id',
            openapi.IN_PATH,
            description="UUID of the course",
            type=openapi.TYPE_STRING,
            format=openapi.FORMAT_UUID
        )
    ],
  security=[{'Bearer': []}]
)
@swagger_auto_schema(
    method='post',
     tags=["Teacher's Course Quize"],
    operation_summary="Create new quiz",
    operation_description="Create a new quiz for a specific course belonging to the authenticated teacher.",
    manual_parameters=[
        openapi.Parameter(
            'course_id',
            openapi.IN_PATH,
            description="UUID of the course",
            type=openapi.TYPE_STRING,
            format=openapi.FORMAT_UUID
        )
    ],
    request_body=TeacherQuizSerializer,
    security=[{'Bearer': []}]
)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def teacher_course_quizzes(request, course_id):
    """
    Get course quizzes or create new quiz
    """
    if request.user.role != 'teacher':
        return Response({
            'success': False,
            'message': 'Access denied. Teacher privileges required.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        teacher = TeacherProfile.objects.get(user=request.user)
        course = Course.objects.get(id=course_id, teacher=teacher)
    except TeacherProfile.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Teacher profile not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Course.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Course not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        quizzes = Quiz.objects.filter(course=course).order_by('order')
        serializer = TeacherQuizSerializer(quizzes, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    
    elif request.method == 'POST':
        serializer = TeacherQuizSerializer(data=request.data)
        if serializer.is_valid():
            # Validate topic belongs to the same course if provided
            topic_id = request.data.get('topic')
            video_id = request.data.get('video')
            
            topic = None
            video = None
            
            if topic_id:
                try:
                    topic = Topic.objects.get(id=topic_id, course=course)
                except Topic.DoesNotExist:
                    return Response({
                        'success': False,
                        'message': 'Topic not found or does not belong to this course'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            if video_id:
                try:
                    video = Video.objects.get(id=video_id, course=course)
                except Video.DoesNotExist:
                    return Response({
                        'success': False,
                        'message': 'Video not found or does not belong to this course'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            serializer.save(course=course,topic=topic,video = video)
            return Response({
                'success': True,
                'message': 'Quiz created successfully',
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'message': 'Quiz creation failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)



# Topic specific quizzes
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teacher_topic_quizzes(request, topic_id):
    """
    Get quizzes for a specific topic
    """
    if request.user.role != 'teacher':
        return Response({
            'success': False,
            'message': 'Access denied. Teacher privileges required.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        teacher = TeacherProfile.objects.get(user=request.user)
        topic = Topic.objects.get(id=topic_id, course__teacher=teacher, is_active=True)
    except TeacherProfile.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Teacher profile not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Topic.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Topic not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        quizzes = Quiz.objects.filter(topic=topic).order_by('order')
        serializer = TeacherQuizSerializer(quizzes, many=True)
        return Response({
            'success': True,
            'data': {
                'topic': topic.title,
                'quizzes': serializer.data
            }
        }, status=status.HTTP_200_OK)

@swagger_auto_schema(
    method='get',
     tags=["Teacher's Course Quize"],
    operation_summary="Get quiz details",
    operation_description="Retrieve details of a specific quiz belonging to the authenticated teacher.",
    manual_parameters=[
        openapi.Parameter(
            'quiz_id',
            openapi.IN_PATH,
            description="UUID of the quiz",
            type=openapi.TYPE_STRING,
            format=openapi.FORMAT_UUID
        )
    ],
   security=[{'Bearer': []}]
)
@swagger_auto_schema(
    method='put',
     tags=["Teacher's Course Quize"],
    operation_summary="Update quiz details",
    operation_description="Update details of a specific quiz belonging to the authenticated teacher.",
    manual_parameters=[
        openapi.Parameter(
            'quiz_id',
            openapi.IN_PATH,
            description="UUID of the quiz",
            type=openapi.TYPE_STRING,
            format=openapi.FORMAT_UUID
        )
    ],
    request_body=TeacherQuizSerializer,
  security=[{'Bearer': []}]
)
@swagger_auto_schema(
    method='delete',
     tags=["Teacher's Course Quize"],
    operation_summary="Delete a quiz",
    operation_description="Delete a specific quiz belonging to the authenticated teacher.",
    manual_parameters=[
        openapi.Parameter(
            'quiz_id',
            openapi.IN_PATH,
            description="UUID of the quiz",
            type=openapi.TYPE_STRING,
            format=openapi.FORMAT_UUID
        )
    ],
 security=[{'Bearer': []}]
)
@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def teacher_quiz_detail(request, quiz_id):
    """
    Get, update or delete specific quiz
    """
    if request.user.role != 'teacher':
        return Response({
            'success': False,
            'message': 'Access denied. Teacher privileges required.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        teacher = TeacherProfile.objects.get(user=request.user)
        quiz = Quiz.objects.get(id=quiz_id, course__teacher=teacher)
    except TeacherProfile.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Teacher profile not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Quiz.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Quiz not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        serializer = TeacherQuizSerializer(quiz)
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    
    elif request.method == 'PUT':
        serializer = TeacherQuizSerializer(quiz, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Quiz updated successfully',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        
        return Response({
            'success': False,
            'message': 'Quiz update failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        quiz.delete()
        return Response({
            'success': True,
            'message': 'Quiz deleted successfully'
        }, status=status.HTTP_200_OK)


# ================================
# Assigments apis
# ==================================


# Assignment views with topic support
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def teacher_course_assignments(request, course_id):
    """
    Get course assignments or create new assignment
    """
    if request.user.role != 'teacher':
        return Response({
            'success': False,
            'message': 'Access denied. Teacher privileges required.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        teacher = TeacherProfile.objects.get(user=request.user)
        course = Course.objects.get(id=course_id, teacher=teacher)
    except TeacherProfile.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Teacher profile not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Course.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Course not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        assignments = Assignment.objects.filter(course=course).order_by('order')
        serializer = TeacherAssignmentSerializer(assignments, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    
    elif request.method == 'POST':
        serializer = TeacherAssignmentSerializer(data=request.data)
        if serializer.is_valid():
            # Validate topic belongs to the same course if provided
            topic_id = request.data.get('topic')
            video_id = request.data.get('video')
            
            topic = None
            video = None
            
            if topic_id:
                try:
                    topic = Topic.objects.get(id=topic_id, course=course)
                except Topic.DoesNotExist:
                    return Response({
                        'success': False,
                        'message': 'Topic not found or does not belong to this course'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            if video_id:
                try:
                    video = Video.objects.get(id=video_id, course=course)
                except Video.DoesNotExist:
                    return Response({
                        'success': False,
                        'message': 'Video not found or does not belong to this course'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            serializer.save(course=course, topic=topic, video=video)
            
            return Response({
                'success': True,
                'message': 'Assignment created successfully',
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'message': 'Assignment creation failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


# Topic specific assignments
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teacher_topic_assignments(request, topic_id):
    """
    Get assignments for a specific topic 
    """
    if request.user.role != 'teacher':
        return Response({
            'success': False,
            'message': 'Access denied. Teacher privileges required.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        teacher = TeacherProfile.objects.get(user=request.user)
        topic = Topic.objects.get(id=topic_id, course__teacher=teacher, is_active=True)
    except TeacherProfile.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Teacher profile not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Topic.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Topic not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        assignments = Assignment.objects.filter(topic=topic).order_by('order')
        serializer = TeacherAssignmentSerializer(assignments, many=True)
        return Response({
            'success': True,
            'data': {
                'topic': topic.title,
                'assignments': serializer.data
            }
        }, status=status.HTTP_200_OK)
    
    


# ==============================
# Teacher Topics create
# ==================================

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def teacher_course_topics(request, course_id):
    """
    Get course topics or create new topic for course
    """
    if request.user.role != 'teacher':
        return Response({
            'success': False,
            'message': 'Access denied. Teacher privileges required.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        teacher = TeacherProfile.objects.get(user=request.user)
        course = Course.objects.get(id=course_id, teacher=teacher)
    except TeacherProfile.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Teacher profile not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Course.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Course not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        topics = Topic.objects.filter(course=course, is_active=True).order_by('order')
        serializer = TeacherTopicSerializer(topics, many=True)
        return Response({
            'success': True,
            'data': {
                'course_title': course.title,
                'total_topics': topics.count(),
                'topics': serializer.data
            }
        }, status=status.HTTP_200_OK)
    
    elif request.method == 'POST':
        # Auto-set order if not provided
        if 'order' not in request.data:
            last_topic = Topic.objects.filter(course=course).order_by('-order').first()
            next_order = (last_topic.order + 1) if last_topic else 1
            request.data['order'] = next_order
        else:
            # Check if order already exists for this course
            order_value = request.data['order']
            if Topic.objects.filter(course=course, order=order_value).exists():
                # Find the next available order
                existing_orders = Topic.objects.filter(
                    course=course, 
                    order__gte=order_value
                ).order_by('order')
                
                # Shift all existing orders by 1
                for topic in existing_orders:
                    topic.order += 1
                    topic.save()

        serializer = TeacherTopicSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(course=course)
            return Response({
                'success': True,
                'message': 'Topic created successfully',
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'message': 'Topic creation failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def teacher_topic_detail(request, topic_id):
    """
    Get, update or delete specific topic
    """
    if request.user.role != 'teacher':
        return Response({
            'success': False,
            'message': 'Access denied. Teacher privileges required.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        teacher = TeacherProfile.objects.get(user=request.user)
        topic = Topic.objects.get(id=topic_id, course__teacher=teacher)
    except TeacherProfile.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Teacher profile not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Topic.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Topic not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        serializer = TeacherTopicSerializer(topic)
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    
    elif request.method == 'PUT':
        serializer = TeacherTopicSerializer(topic, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Topic updated successfully',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        
        return Response({
            'success': False,
            'message': 'Topic update failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        # Soft delete - just set is_active to False
        topic.is_active = False
        topic.save()
        return Response({
            'success': True,
            'message': 'Topic deleted successfully'
        }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teacher_topic_content(request, topic_id):
    """
    Get all content (videos, quizzes, assignments) for a specific topic
    """
    if request.user.role != 'teacher':
        return Response({
            'success': False,
            'message': 'Access denied. Teacher privileges required.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        teacher = TeacherProfile.objects.get(user=request.user)
        topic = Topic.objects.get(id=topic_id, course__teacher=teacher, is_active=True)
    except TeacherProfile.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Teacher profile not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Topic.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Topic not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Get all related content
    videos = Video.objects.filter(topic=topic).order_by('order')
    quizzes = Quiz.objects.filter(topic=topic).order_by('order')
    assignments = Assignment.objects.filter(topic=topic).order_by('order')
    
    # Serialize the data
    video_serializer = TeacherVideoSerializer(videos, many=True)
    quiz_serializer = TeacherQuizSerializer(quizzes, many=True)
    assignment_serializer = TeacherAssignmentSerializer(assignments, many=True)
    topic_serializer = TeacherTopicSerializer(topic)
    
    return Response({
        'success': True,
        'data': {
            'topic': topic_serializer.data,
            'videos': video_serializer.data,
            'quizzes': quiz_serializer.data,
            'assignments': assignment_serializer.data,
            'stats': {
                'total_videos': videos.count(),
                'total_quizzes': quizzes.count(),
                'total_assignments': assignments.count(),
                'total_duration': topic.get_total_duration()
            }
        }
    }, status=status.HTTP_200_OK)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def teacher_topics_reorder(request, course_id):
    """
    Reorder topics for a course
    Expected data: {'topic_orders': [{'id': 1, 'order': 1}, {'id': 2, 'order': 2}]}
    """
    if request.user.role != 'teacher':
        return Response({
            'success': False,
            'message': 'Access denied. Teacher privileges required.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        teacher = TeacherProfile.objects.get(user=request.user)
        course = Course.objects.get(id=course_id, teacher=teacher)
    except (TeacherProfile.DoesNotExist, Course.DoesNotExist):
        return Response({
            'success': False,
            'message': 'Course or teacher profile not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    topic_orders = request.data.get('topic_orders', [])
    
    if not topic_orders:
        return Response({
            'success': False,
            'message': 'topic_orders data required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        with transaction.atomic():
            # First, reset all orders to very high temporary values
            temp_base = 10000  # High enough to avoid conflicts
            all_topics = Topic.objects.filter(course=course)
            for topic in all_topics:
                topic.order = temp_base + topic.id
                topic.save()
            
            # Now set the new orders
            for item in topic_orders:
                topic = Topic.objects.get(id=item['id'], course=course)
                topic.order = item['order']
                topic.save()
        
        return Response({
            'success': True,
            'message': 'Topics reordered successfully'
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Reorder failed: {str(e)}'
        }, status=status.HTTP_400_BAD_REQUEST)


# ====================================
# Teacher Course Live classes
# =======================================


@swagger_auto_schema(
    method='get',
    tags=["Teacher Course Live classes"],
    operation_summary="List course live classes",
    operation_description="Retrieve all scheduled live classes for a specific course belonging to the authenticated teacher.",
    manual_parameters=[
        openapi.Parameter(
            'course_id',
            openapi.IN_PATH,
            description="UUID of the course",
            type=openapi.TYPE_STRING,
            format=openapi.FORMAT_UUID
        )
    ],
  security=[{'Bearer': []}]
)
@swagger_auto_schema(
    method='post',
    tags=["Teacher Course Live classes"],
    operation_summary="Schedule new live class",
    operation_description="Schedule a new live class for a specific course and notify enrolled students.",
    manual_parameters=[
        openapi.Parameter(
            'course_id',
            openapi.IN_PATH,
            description="UUID of the course",
            type=openapi.TYPE_STRING,
            format=openapi.FORMAT_UUID
        )
    ],
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['title', 'scheduled_time'],
        properties={
            'title': openapi.Schema(type=openapi.TYPE_STRING),
            'scheduled_time': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
            'max_participants': openapi.Schema(type=openapi.TYPE_INTEGER),
            'is_recorded': openapi.Schema(type=openapi.TYPE_BOOLEAN),
            'waiting_room': openapi.Schema(type=openapi.TYPE_BOOLEAN)
        }
    ),
   security=[{'Bearer': []}]
)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated, IsTeacher])
def teacher_course_live_classes(request, course_id):
    """
    Get course live classes or schedule new live class
    """
    # if not hasattr(request.user, 'teacher_profile'):
    #     return Response({
    #         'success': False,
    #         'message': 'Access denied. Teacher privileges required.'
    #     }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        teacher = TeacherProfile.objects.get(user=request.user)
        course = Course.objects.get(id=course_id, teacher=teacher)
    except TeacherProfile.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Teacher profile not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Course.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Course not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        
       
        
        live_classes = Meeting.objects.filter(
            course=course, 
            meeting_type='lecture'
        ).order_by('-scheduled_time')
        
        serializer = LiveClassSerializer(live_classes, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)


    elif request.method == 'POST':
        scheduled_time_str = request.data.get('scheduled_time')
        try:
            scheduled_time = datetime.fromisoformat(scheduled_time_str)
        except ValueError:
            return Response({
                'success': False,
                'message': 'Invalid datetime format. Expected ISO format (YYYY-MM-DDTHH:MM[:SS])'
            }, status=status.HTTP_400_BAD_REQUEST)
                
        # Create live class meeting
        meeting = Meeting.objects.create(
            host=request.user,
            course=course,
            title=request.data.get('title', f'{course.title} - Live Class'),
            meeting_type='lecture',
            scheduled_time=scheduled_time,
            max_participants=request.data.get('max_participants', 100),
            is_recorded=request.data.get('is_recorded', False),
            is_waiting_room_enabled=request.data.get('waiting_room', True)
        )
        
        
        verified_enrollments = Enrollment.objects.filter( course=course, payment_status='verified')

        # Send invites
        for enrollment in verified_enrollments:
            student_email = enrollment.student.email
            try:
                send_mail(
                    subject=f"📢 New Live Class for {course.title}",
                    message=f"Dear {enrollment.student.get_full_name()},\n\nYou are invited to attend a live class titled '{meeting.title}' scheduled on {meeting.scheduled_time}. Don't miss it!\n\nRegards,\n{teacher.user.get_full_name()}",
                    from_email='no-reply@lms.com',
                    recipient_list=[student_email],
                    fail_silently=True
                )
            except Exception as e:
                print(f"Failed to send invite to {student_email}: {str(e)}")

        serializer = LiveClassSerializer(meeting)
        
        return Response({
            'success': True,
            'message': 'Live class scheduled successfully',
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)



@swagger_auto_schema(
    method='get',
    tags=["Teacher Course Live classes"],
    operation_summary="Get live class details",
    operation_description="Retrieve details of a specific live class belonging to the authenticated teacher.",
    manual_parameters=[
        openapi.Parameter(
            'class_id',
            openapi.IN_PATH,
            description="UUID of the live class",
            type=openapi.TYPE_STRING,
            format=openapi.FORMAT_UUID
        )
    ],
    security=[{'Bearer': []}]
)
@swagger_auto_schema(
    method='put',
    tags=["Teacher Course Live classes"],
    operation_summary="Update live class details",
    operation_description="Update details of a specific live class belonging to the authenticated teacher.",
    manual_parameters=[
        openapi.Parameter(
            'class_id',
            openapi.IN_PATH,
            description="UUID of the live class",
            type=openapi.TYPE_STRING,
            format=openapi.FORMAT_UUID
        )
    ],
    request_body=LiveClassSerializer,
  security=[{'Bearer': []}]
)
@swagger_auto_schema(
    method='delete',
    tags=["Teacher Course Live classes"],
    operation_summary="Cancel a live class",
    operation_description="Cancel a specific live class belonging to the authenticated teacher.",
    manual_parameters=[
        openapi.Parameter(
            'class_id',
            openapi.IN_PATH,
            description="UUID of the live class",
            type=openapi.TYPE_STRING,
            format=openapi.FORMAT_UUID
        )
    ],
 security=[{'Bearer': []}]
)
@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def teacher_live_class_detail(request, class_id):
    """
    Get, update or delete specific live class
    """
    if request.user.role != 'teacher':
        return Response({
            'success': False,
            'message': 'Access denied. Teacher privileges required.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        teacher = TeacherProfile.objects.get(user=request.user)

        live_class = Meeting.objects.get(
            id=class_id, 
            course__teacher=teacher,
            meeting_type='lecture'
        )
    except TeacherProfile.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Teacher profile not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Meeting.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Live class not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        serializer = LiveClassSerializer(live_class)
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    
    elif request.method == 'PUT':
        # Update live class details
        allowed_fields = ['title', 'scheduled_time', 'max_participants', 'is_recorded']
        for field in allowed_fields:
            if field in request.data:
                setattr(live_class, field, request.data[field])
        
        live_class.save()
        
      
        serializer = LiveClassSerializer(live_class)
        return Response({
            'success': True,
            'message': 'Live class updated successfully',
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    
    elif request.method == 'DELETE':
        if live_class.status == 'active':
            return Response({
                'success': False,
                'message': 'Cannot delete active live class'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        live_class.delete()
        return Response({
            'success': True,
            'message': 'Live class deleted successfully'
        }, status=status.HTTP_200_OK)
    

    