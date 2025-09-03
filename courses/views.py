# courses/views.py

from rest_framework import status, filters
from rest_framework.decorators import api_view,permission_classes
from rest_framework.response import Response
from rest_framework.generics import ListAPIView
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from rest_framework.permissions import   AllowAny
from django.db.models import Count
from django.shortcuts import get_object_or_404
from support_feedback.models import CourseFeedback
from django.db.models import Prefetch
from .models import Course, Video, Quiz, Assignment,Enrollment,Topic
from meetings.models import Meeting
from .serializers import (
    CourseListSerializer, CourseDetailSerializer, VideoDetailSerializer,
    QuizSerializer, AssignmentSerializer,TeacherSerializer,CourseWithTopicsSerializer,TopicDetailSerializer,TopicSerializer,
    VideoWithTopicSerializer,VideoSerializer
)
from authentication.models import TeacherProfile,User


class CourseListView(ListAPIView):
    """
    Course listing with filtering, search, ordering, and featured option
    """
    serializer_class = CourseDetailSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['course_type', 'teacher', 'is_active']
    search_fields = ['title', 'description', 'teacher__user__username']
    ordering_fields = ['created_at', 'title', 'price']
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = Course.objects.filter(is_active=True).select_related('teacher__user').prefetch_related('topics')
        
        # 🔍 Search by ?q=
        query = self.request.query_params.get('q')
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query) |
                Q(teacher__user__username__icontains=query) |
                Q(topics__title__incontains=query)
            )

        # 🎯 Filter by price
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)

        # 🌟 Featured courses (most enrolled)
        is_featured = self.request.query_params.get('featured')
        if is_featured == 'true':
            queryset = queryset.annotate(
                enrollment_count=Count('enrollments')
            ).order_by('-enrollment_count')[:6]

        return queryset


@api_view(['GET'])
@permission_classes([AllowAny])
def course_detail(request, course_id):
    """
    Get detailed information about a specific course
    """
    try:
        course = Course.objects.select_related('teacher__user').prefetch_related(
            'topics__videos__quizzes',
            'topics__videos__assignments',
            'topics__quizzes',
            'topics__assignments',
            'reviews'  ).get(id=course_id, is_active=True)
        
        serializer = CourseDetailSerializer(course,context = {'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Course.DoesNotExist:
        return Response(
            {'error': 'Course not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )



# ===== NEW TOPIC-BASED APIS =====

@api_view(['GET'])
@permission_classes([AllowAny])
def course_topics(request, course_id):
    """
    Get all topics for a specific course
    """
    try:
        course = Course.objects.get(id=course_id, is_active=True)
        topics = Topic.objects.filter(course=course, is_active=True).prefetch_related('videos').order_by('order')
        
        serializer = TopicSerializer(topics, many=True)
        return Response({
            'course_id': course_id,
            'course_title': course.title,
            'total_topics': topics.count(),
            'topics': serializer.data
        }, status=status.HTTP_200_OK)
        
    except Course.DoesNotExist:
        return Response(
            {'error': 'Course not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def topic_detail(request, topic_id):
    """
    Get detailed information about a specific topic with all videos
    """
    try:
        topic = Topic.objects.select_related('course').prefetch_related(
            'videos__quizzes',
            'videos__assignments',
            'quizzes',
            'assignments'
        ).get(id=topic_id, is_active=True)
        
        # Check if user has access to the course
        user_has_access = True
        if hasattr(request, 'user') and request.user.is_authenticated:
            user_has_access = topic.course.has_user_paid(request.user)
        elif topic.course.course_type == 'paid':
            user_has_access = False
        
        serializer = TopicDetailSerializer(topic)
        data = serializer.data
        data['user_has_access'] = user_has_access
        data['course_title'] = topic.course.title
        data['course_type'] = topic.course.course_type
        
        return Response(data, status=status.HTTP_200_OK)
        
    except Topic.DoesNotExist:
        return Response(
            {'error': 'Topic not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def topic_videos(request, topic_id):
    """
    Get all videos for a specific topic
    """
    try:
        topic = Topic.objects.select_related('course').get(id=topic_id, is_active=True)
        videos = Video.objects.filter(topic=topic).order_by('order')
        if not videos:
            return Response(
            {'error': 'Video not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
        
        # Check access
        user_has_access = True
        if hasattr(request, request.user) and request.user.is_authenticated:
            user_has_access = topic.course.has_user_paid(request.user)
        elif topic.course.course_type == 'paid':
            user_has_access = False
        
        video_data = []
        for video in videos:
            # Show free preview videos or if user has access
            if user_has_access or video.is_free_preview:
                video_info = {
                    'id': video.id,
                    'title': video.title,
                    'description': video.description,
                    'duration': video.duration,
                    'order': video.order,
                    'has_quiz': video.quizzes.exists(),
                    'has_assignment': video.assignments.exists(),
                    'is_free_preview': video.is_free_preview,
                    'can_access': True
                }
            else:
                video_info = {
                    'id': video.id,
                    'title': video.title,
                    'description': 'Premium content - Purchase course to access',
                    'duration': video.duration,
                    'order': video.order,
                    'has_quiz': video.quizzes.exists(),
                    'has_assignment': video.assignments.exists(),
                    'is_free_preview': False,
                    'can_access': False
                }
            video_data.append(video_info)
        
        return Response({
            'topic_id': topic_id,
            'topic_title': topic.title,
            'course_title': topic.course.title,
            'course_type': topic.course.course_type,
            'user_has_access': user_has_access,
            'videos': video_data
        }, status=status.HTTP_200_OK)
        
    except Topic.DoesNotExist:
        return Response(
            {'error': 'Topic not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    except Video.DoesNotExist:
        return Response(
            {'error': 'Video not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def video_detail_with_topic(request, video_id):
    """
    Get detailed information about a specific video with topic context
    """
    try:
        video = Video.objects.select_related(
            'course', 'topic'
        ).prefetch_related(
            'quizzes__questions', 'assignments'
        ).get(id=video_id)
        
        # Check access
        user_has_access = True
        if hasattr(request, 'user') and request.user.is_authenticated:
            user_has_access = video.course.has_user_paid(request.user)
        elif video.course.course_type == 'paid' and not video.is_free_preview:
            user_has_access = False
        
        if not user_has_access and not video.is_free_preview:
            return Response(
                {'error': 'Access denied. Purchase the course to watch this video.'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get next and previous videos in the same topic
        next_video = Video.objects.filter(
            topic=video.topic, order__gt=video.order
        ).order_by('order').first()
        
        prev_video = Video.objects.filter(
            topic=video.topic, order__lt=video.order
        ).order_by('-order').first()
        
        serializer = VideoWithTopicSerializer(video)
        data = serializer.data
        
        # Add navigation info
        data['topic_id'] = video.topic.id if video.topic else None
        data['topic_title'] = video.topic.title if video.topic else None
        data['course_id'] = video.course.id
        data['course_title'] = video.course.title
        data['next_video_id'] = next_video.id if next_video else None
        data['prev_video_id'] = prev_video.id if prev_video else None
        data['user_has_access'] = user_has_access
        
        return Response(data, status=status.HTTP_200_OK)
        
    except Video.DoesNotExist:
        return Response(
            {'error': 'Video not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def video_detail(request, video_id):
    """
    Get detailed information about a specific video with related quizzes and assignments
    """
    try:
        video = Video.objects.select_related('course').prefetch_related(
            'quizzes', 'assignments'
        ).get(id=video_id)
        
        serializer = VideoDetailSerializer(video)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Video.DoesNotExist:
        return Response(
            {'error': 'Video not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def course_videos(request, course_id):
    """
    Get all videos for a specific course (for sidebar playlist)
    """
    try:
        course = Course.objects.get(id=course_id, is_active=True)
        user_has_access = True
        if hasattr(request, 'user') and request.user.is_authenticated:
            user_has_access = course.has_user_paid(request.user)
        elif course.course_type == 'paid':
            user_has_access = False

        topics = Topic.objects.filter(course=course, is_active=True).prefetch_related('videos').order_by('order')

        videos = Video.objects.filter(course=course).order_by('order')
        
        # Add progress information for each video (you can expand this later)
        topics_data = []
        for topic in topics:
            videos_data = []
            for video in topic.videos.order_by('order'):
                if user_has_access or video.is_free_preview:
                    video_info = {
                        'id': video.id,
                        'title': video.title,
                        'duration': video.duration,
                        'order': video.order,
                        'has_quiz': video.quizzes.exists(),
                        'has_assignment': video.assignments.exists(),
                        'is_free_preview': video.is_free_preview,
                        'can_access': True
                    }
                else:
                    video_info = {
                        'id': video.id,
                        'title': video.title,
                        'duration': video.duration,
                        'order': video.order,
                        'has_quiz': video.quizzes.exists(),
                        'has_assignment': video.assignments.exists(),
                        'is_free_preview': False,
                        'can_access': False
                    }
                videos_data.append(video_info)
            
            topics_data.append({
                'id': topic.id,
                'title': topic.title,
                'order': topic.order,
                'video_count': len(videos_data),
                'videos': videos_data
            })
        
        return Response({
            'course_id': course_id,
            'course_title': course.title,
            'course_type': course.course_type,
            'user_has_access': user_has_access,
            'total_topics': len(topics_data),
            'topics': topics_data
        }, status=status.HTTP_200_OK)
        
    except Course.DoesNotExist:
        return Response(
            {'error': 'Course not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def video_quiz_assignments(request, video_id):
    """
    Get quizzes and assignments for a specific video
    """
    try:
        video = Video.objects.get(id=video_id)
        
        quizzes = Quiz.objects.filter(video=video).order_by('order')
        assignments = Assignment.objects.filter(video=video).order_by('order')
        
        quiz_serializer = QuizSerializer(quizzes, many=True)
        assignment_serializer = AssignmentSerializer(assignments, many=True)
        
        return Response({
            'video_id': video_id,
            'video_title': video.title,
            'quizzes': quiz_serializer.data,
            'assignments': assignment_serializer.data
        }, status=status.HTTP_200_OK)
        
    except Video.DoesNotExist:
        return Response(
            {'error': 'Video not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )




# =======================
# Get teachers Profile
# =========================
@api_view(['GET'])
@permission_classes([AllowAny])
def list_all_teachers(request):
    """
    List all teachers for students to browse.
    """
    # if request.user.role != 'student':
    #     return Response({
    #         "success": False,
    #         "message": "Access denied. Student privileges required."
    #     }, status=status.HTTP_403_FORBIDDEN)

    teachers = TeacherProfile.objects.select_related('user').filter(user__role='teacher')
    serializer = TeacherSerializer(teachers, many=True,context={"request":request})
    return Response({
        "success": True,
        "data": serializer.data
    }, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([AllowAny])
def view_teacher_profile(request, teacher_id):
    """
    View details of a specific teacher profile.
    """
    try:
        teacher = get_object_or_404(
            TeacherProfile.objects.select_related('user'),
            id=teacher_id,  # or user__id=teacher_id depending on your needs
            user__role='teacher'
        )
        serializer = TeacherSerializer(teacher,context={'request':request})
        courses = Course.objects.filter(teacher=teacher)
        # total_courses = courses.count()
        # active_courses = courses.filter(is_active=True).count()
        # total_students = Enrollment.objects.filter(course__teacher=teacher).count()
        # total_videos = Video.objects.filter(course__teacher=teacher).count()
        # total_quizzes = Quiz.objects.filter(course__teacher=teacher).count()
        # total_live_classes = Meeting.objects.filter(course__teacher=teacher, meeting_type='lecture').count()

        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except TeacherProfile.DoesNotExist:
        return Response(
            {'error': 'Teacher profile not found'},
            status=status.HTTP_404_NOT_FOUND
        )