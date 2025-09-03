# job_board/permissions.py

from rest_framework import permissions
from authentication.models import StudentProfile, TeacherProfile


class IsStudentUser(permissions.BasePermission):
    """
    Permission to only allow students to create job posts.
    """
    
    def has_permission(self, request, view):
        print("Studnet is come: ",request.user.role)
        print("Request: ",request.user.is_authenticated)
        if not request.user.is_authenticated:
            return False
        print("ok")
        
        return getattr(request.user, "role", "").lower() == "student"
    print("requuest")
    
    def has_object_permission(self, request, view, obj):
        # For job posts, check if user is the owner
        print("oobject user: ",obj.student.user)
        if hasattr(obj, 'student'):
            return obj.student.user == request.user
        return False


class IsTeacherUser(permissions.BasePermission):
    """
    Permission to only allow teachers to apply for jobs.
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        return hasattr(request.user, 'teacher_profile')
    
    def has_object_permission(self, request, view, obj):
        # For job applications, check if user is the applicant
        if hasattr(obj, 'teacher'):
            return obj.teacher.user == request.user
        return False


class IsJobOwnerOrReadOnly(permissions.BasePermission):
    """
    Permission to allow job owners to edit their posts, others can only read.
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Allow read permissions for authenticated users
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # For write permissions, check in has_object_permission
        return True
    
    def has_object_permission(self, request, view, obj):
        # Read permissions for any authenticated user
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions only for job owner
        if hasattr(obj, 'student'):
            return obj.student.user == request.user
        
        return False


class IsApplicationOwnerOrJobOwner(permissions.BasePermission):
    """
    Permission for job applications:
    - Application owner (teacher) can read their application
    - Job owner (student) can read/update applications for their jobs
    """
    
    def has_permission(self, request, view):
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Teacher who applied can read their application
        if hasattr(obj, 'teacher') and hasattr(request.user, 'teacher_profile'):
            if obj.teacher.user == request.user:
                return request.method in permissions.SAFE_METHODS
        
        # Student who owns the job can read/update applications
        if hasattr(obj, 'job_post') and hasattr(request.user, 'student_profile'):
            if obj.job_post.student.user == request.user:
                return True
        
        return False


class CanApplyToJob(permissions.BasePermission):
    """
    Permission to check if a teacher can apply to a specific job.
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Must be a teacher
        if not hasattr(request.user, 'teacher_profile'):
            return False
        
        # Get job_post from view kwargs or context
        job_post_id = view.kwargs.get('job_id') or view.kwargs.get('pk')
        if not job_post_id:
            return False
        
        try:
            from .models import JobPost, JobApplication
            job_post = JobPost.objects.get(id=job_post_id)
            
            # Job must be open
            if job_post.status != 'open':
                return False
            
            # Teacher shouldn't have already applied
            if JobApplication.objects.filter(
                job_post=job_post,
                teacher=request.user.teacher_profile
            ).exists():
                return False
            
            return True
            
        except JobPost.DoesNotExist:
            return False


class IsStudentOrTeacher(permissions.BasePermission):
    """
    Permission to allow both students and teachers.
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        return (
            hasattr(request.user, 'student_profile') or 
            hasattr(request.user, 'teacher_profile')
        )


class CanReviewJob(permissions.BasePermission):
    """
    Permission to allow reviewing a completed job.
    Only participants (student and selected teacher) can review.
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        job_post_id = view.kwargs.get('job_id')
        if not job_post_id:
            return False
        
        try:
            from .models import JobPost
            job_post = JobPost.objects.get(id=job_post_id)
            
            # Job must be completed
            if job_post.status != 'completed':
                return False
            
            # User must be either the student or the selected teacher
            user_is_student = (
                hasattr(request.user, 'student_profile') and
                job_post.student.user == request.user
            )
            user_is_teacher = (
                hasattr(request.user, 'teacher_profile') and
                job_post.selected_teacher and
                job_post.selected_teacher.user == request.user
            )
            
            return user_is_student or user_is_teacher
            
        except JobPost.DoesNotExist:
            return False


class IsJobParticipant(permissions.BasePermission):
    """
    Permission for actions that require being part of the job
    (either student who posted or selected teacher).
    """
    
    def has_object_permission(self, request, view, obj):
        # For JobPost objects
        if hasattr(obj, 'student'):
            # Student owner
            if hasattr(request.user, 'student_profile'):
                if obj.student.user == request.user:
                    return True
            
            # Selected teacher
            if hasattr(request.user, 'teacher_profile'):
                if obj.selected_teacher and obj.selected_teacher.user == request.user:
                    return True
        
        return False