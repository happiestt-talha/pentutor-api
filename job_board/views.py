# job_board/views.py

from rest_framework import generics, status, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated,AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.db import transaction

from .models import JobPost, JobApplication, JobReview
from .serializers import (
    JobPostCreateSerializer, JobPostListSerializer, JobPostDetailSerializer,
    JobApplicationCreateSerializer, JobApplicationBasicSerializer,
    JobApplicationDetailSerializer, JobApplicationUpdateSerializer,
    JobPostUpdateSerializer, JobReviewSerializer,
    MyJobPostSerializer, MyJobApplicationSerializer
)
from .permissions import (
    IsStudentUser, IsTeacherUser, IsJobOwnerOrReadOnly,
    IsApplicationOwnerOrJobOwner, CanApplyToJob, IsStudentOrTeacher,
    CanReviewJob, IsJobParticipant
)
from .filters import JobPostFilter


# Job Post Views
class JobPostListView(generics.ListAPIView):
    """
    List all open job posts. Available to both students and teachers.
    """
    queryset = JobPost.objects.filter(status='open').select_related(
        'student__user', 'course', 'selected_teacher__user'
    ).prefetch_related('applications')
    serializer_class = JobPostListSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = JobPostFilter
    search_fields = ['title', 'description', 'subject_text', 'course__name']
    ordering_fields = ['created_at', 'budget_amount', 'deadline']
    ordering = ['-created_at']


class JobPostCreateView(generics.CreateAPIView):
    """
    Create a new job post. Only students can create job posts.
    """
    queryset = JobPost.objects.all()
    serializer_class = JobPostCreateSerializer
    print("ok")
    permission_classes = [IsAuthenticated, IsStudentUser]
    print("studentUser")

    def create(self, request, *args, **kwargs):
        try:
            response = super().create(request, *args, **kwargs)
            return Response({
                'success': True,
                'message': 'Job post created successfully!',
                'data': response.data
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({
                'success': False,
                'message': 'Failed to create job post.',
                'errors': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class JobPostDetailView(generics.RetrieveUpdateAPIView):
    """
    Retrieve and update a specific job post.
    """
    queryset = JobPost.objects.select_related(
        'student__user', 'course', 'selected_teacher__user'
    ).prefetch_related('applications__teacher__user')
    serializer_class = JobPostDetailSerializer
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return JobPostUpdateSerializer
        return JobPostDetailSerializer

    def update(self, request, *args, **kwargs):
        try:
            response = super().update(request, *args, **kwargs)
            return Response({
                'success': True,
                'message': 'Job post updated successfully!',
                'data': response.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'success': False,
                'message': 'Failed to update job post.',
                'errors': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


# Job Application Views
class JobApplicationCreateView(generics.CreateAPIView):
    """
    Apply to a specific job post. Only teachers can apply.
    """
    queryset = JobApplication.objects.all()
    serializer_class = JobApplicationCreateSerializer
    permission_classes = [IsAuthenticated, CanApplyToJob]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        # Short-circuit during schema generation
        if getattr(self, 'swagger_fake_view', False):
            return context
        job_post = get_object_or_404(JobPost, id=self.kwargs['job_id'])
        context['job_post'] = job_post
        return context

    def create(self, request, *args, **kwargs):
        try:
            response = super().create(request, *args, **kwargs)
            return Response({
                'success': True,
                'message': 'Application submitted successfully!',
                'data': response.data
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({
                'success': False,
                'message': 'Failed to submit application.',
                'errors': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class JobApplicationListView(generics.ListAPIView):
    """
    List applications for a specific job post. Only job owner can see this.
    """
    serializer_class = JobApplicationBasicSerializer
    permission_classes = [IsAuthenticated, IsStudentOrTeacher]

    def get_queryset(self):
        job_post = get_object_or_404(JobPost, id=self.kwargs['job_id'])
        # Ensure the requesting student owns this job
        if job_post.student.user != self.request.user:
            return JobApplication.objects.none()
        
        return JobApplication.objects.filter(job_post=job_post).select_related(
            'teacher__user'
        ).order_by('-applied_at')

    def list(self, request, *args, **kwargs):
        try:
            response = super().list(request, *args, **kwargs)
            return Response({
                'success': True,
                'message': 'Applications retrieved successfully!',
                'data': response.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'success': False,
                'message': 'Failed to retrieve applications.',
                'errors': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class JobApplicationDetailView(generics.RetrieveUpdateAPIView):
    """
    Retrieve and update a specific job application.
    """
    queryset = JobApplication.objects.select_related(
        'teacher__user', 'job_post__student__user'
    )
    serializer_class = JobApplicationDetailSerializer
    permission_classes = [IsAuthenticated, IsApplicationOwnerOrJobOwner]

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return JobApplicationUpdateSerializer
        return JobApplicationDetailSerializer

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        try:
            application = self.get_object()
            
            # If accepting an application, update job post
            if request.data.get('status') == 'accepted':
                job_post = application.job_post
                job_post.status = 'accepted'
                job_post.selected_teacher = application.teacher
                job_post.save()
                
                # Reject all other applications for this job
                JobApplication.objects.filter(
                    job_post=job_post
                ).exclude(id=application.id).update(status='rejected')
            
            response = super().update(request, *args, **kwargs)
            return Response({
                'success': True,
                'message': 'Application updated successfully!',
                'data': response.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'success': False,
                'message': 'Failed to update application.',
                'errors': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


# Dashboard Views
class StudentDashboardView(generics.ListAPIView):
    """
    Student dashboard showing their job posts.
    """
    serializer_class = MyJobPostSerializer
    permission_classes = [IsAuthenticated, IsStudentUser]

    def get_queryset(self):
        return JobPost.objects.filter(
            student__user=self.request.user
        ).select_related('course', 'selected_teacher__user').prefetch_related(
            'applications'
        ).order_by('-created_at')

    def list(self, request, *args, **kwargs):
        try:
            response = super().list(request, *args, **kwargs)
            
            # Add summary statistics
            queryset = self.get_queryset()
            stats = {
                'total_jobs': queryset.count(),
                'open_jobs': queryset.filter(status='open').count(),
                'accepted_jobs': queryset.filter(status='accepted').count(),
                'completed_jobs': queryset.filter(status='completed').count(),
                'total_applications': sum(job.applications_count for job in queryset)
            }
            
            return Response({
                'success': True,
                'message': 'Dashboard data retrieved successfully!',
                'stats': stats,
                'jobs': response.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'success': False,
                'message': 'Failed to retrieve dashboard data.',
                'errors': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class TeacherDashboardView(generics.ListAPIView):
    """
    Teacher dashboard showing their job applications.
    """
    serializer_class = MyJobApplicationSerializer
    permission_classes = [IsAuthenticated, IsTeacherUser]

    def get_queryset(self):
        return JobApplication.objects.filter(
            teacher__user=self.request.user
        ).select_related('job_post__student__user', 'job_post__course').order_by('-applied_at')

    def list(self, request, *args, **kwargs):
        try:
            response = super().list(request, *args, **kwargs)
            
            # Add summary statistics
            queryset = self.get_queryset()
            stats = {
                'total_applications': queryset.count(),
                'pending_applications': queryset.filter(status='pending').count(),
                'accepted_applications': queryset.filter(status='accepted').count(),
                'rejected_applications': queryset.filter(status='rejected').count(),
            }
            
            return Response({
                'success': True,
                'message': 'Dashboard data retrieved successfully!',
                'stats': stats,
                'applications': response.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'success': False,
                'message': 'Failed to retrieve dashboard data.',
                'errors': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


# Job Review Views
class JobReviewCreateView(generics.CreateAPIView):
    """
    Create a review for a completed job.
    """
    queryset = JobReview.objects.all()
    serializer_class = JobReviewSerializer
    permission_classes = [IsAuthenticated, CanReviewJob]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        # Short-circuit during schema generation
        if getattr(self, 'swagger_fake_view', False):
            return context
        job_post = get_object_or_404(JobPost, id=self.kwargs['job_id'])
        context['job_post'] = job_post
        return context

    def create(self, request, *args, **kwargs):
        try:
            response = super().create(request, *args, **kwargs)
            return Response({
                'success': True,
                'message': 'Review submitted successfully!',
                'data': response.data
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({
                'success': False,
                'message': 'Failed to submit review.',
                'errors': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


# API endpoint functions
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsJobParticipant])
def schedule_meeting_for_job(request, job_id):
    """
    Schedule a meeting for an accepted job.
    This integrates with your Meeting app.
    """
    try:
        job_post = get_object_or_404(JobPost, id=job_id)
        
        # Check if job is accepted and user is participant
        if job_post.status not in ['accepted', 'in_progress']:
            return Response({
                'success': False,
                'message': 'Meeting can only be scheduled for accepted jobs.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Here you would integrate with your Meeting app
        # Example: create a meeting with both participants
        meeting_data = {
            'title': f"Job Meeting: {job_post.title}",
            'participants': [job_post.student.user.id, job_post.selected_teacher.user.id],
            'job_related': job_post.id,
            # Add other meeting fields as needed
        }
        
        # This would call your Meeting app's API or create meeting directly
        # For now, returning a placeholder response
        return Response({
            'success': True,
            'message': 'Meeting scheduling initiated!',
            'data': {
                'job_id': job_post.id,
                'meeting_data': meeting_data,
                'redirect_url': f'/meetings/create/?job_id={job_id}'
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'message': 'Failed to schedule meeting.',
            'errors': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsStudentOrTeacher])
def job_statistics(request):
    """
    Get overall job board statistics.
    """
    try:
        stats = {
            'total_jobs': JobPost.objects.count(),
            'open_jobs': JobPost.objects.filter(status='open').count(),
            'completed_jobs': JobPost.objects.filter(status='completed').count(),
            'total_applications': JobApplication.objects.count(),
            # 'average_budget': JobPost.objects.aggregate(
            #     avg_budget=models.Avg('budget_amount')
            # )['avg_budget'] or 0,
        }
        
        # User-specific stats
        if hasattr(request.user, 'studentprofile'):
            user_stats = {
                'my_jobs': JobPost.objects.filter(student__user=request.user).count(),
                'my_completed_jobs': JobPost.objects.filter(
                    student__user=request.user, status='completed'
                ).count(),
            }
        elif hasattr(request.user, 'teacherprofile'):
            user_stats = {
                'my_applications': JobApplication.objects.filter(
                    teacher__user=request.user
                ).count(),
                'my_accepted_jobs': JobApplication.objects.filter(
                    teacher__user=request.user, status='accepted'
                ).count(),
            }
        else:
            user_stats = {}
        
        return Response({
            'success': True,
            'message': 'Statistics retrieved successfully!',
            'general_stats': stats,
            'user_stats': user_stats
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'message': 'Failed to retrieve statistics.',
            'errors': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsStudentUser])
def cancel_job(request, job_id):
    """
    Cancel a job post. Only job owner can cancel.
    """
    try:
        job_post = get_object_or_404(JobPost, id=job_id)
        
        # Check ownership
        if job_post.student.user != request.user:
            return Response({
                'success': False,
                'message': 'You can only cancel your own jobs.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Check if job can be cancelled
        if job_post.status in ['completed', 'cancelled']:
            return Response({
                'success': False,
                'message': 'Job cannot be cancelled in its current status.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        job_post.status = 'cancelled'
        job_post.save()
        
        # Reject all pending applications
        JobApplication.objects.filter(
            job_post=job_post, status='pending'
        ).update(status='rejected')
        
        return Response({
            'success': True,
            'message': 'Job cancelled successfully!'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'message': 'Failed to cancel job.',
            'errors': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_job_completed(request, job_id):
    """
    Mark a job as completed. Either student or teacher can do this.
    """
    try:
        job_post = get_object_or_404(JobPost, id=job_id)
        
        # Check if user is participant
        user_is_student = (
            hasattr(request.user, 'studentprofile') and
            job_post.student.user == request.user
        )
        user_is_teacher = (
            hasattr(request.user, 'teacherprofile') and
            job_post.selected_teacher and
            job_post.selected_teacher.user == request.user
        )
        
        if not (user_is_student or user_is_teacher):
            return Response({
                'success': False,
                'message': 'Only job participants can mark it as completed.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Check if job is in progress
        if job_post.status != 'in_progress':
            return Response({
                'success': False,
                'message': 'Only jobs in progress can be marked as completed.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        job_post.status = 'completed'
        job_post.save()
        
        return Response({
            'success': True,
            'message': 'Job marked as completed successfully!'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'message': 'Failed to mark job as completed.',
            'errors': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)