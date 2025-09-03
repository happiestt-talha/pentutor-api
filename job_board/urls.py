# job_board/urls.py

from django.urls import path
from . import views

app_name = 'job_board'

urlpatterns = [
    # Job Post URLs
    path('jobs/', views.JobPostListView.as_view(), name='job_list'),
    path('jobs/create/', views.JobPostCreateView.as_view(), name='job_create'),
    path('jobs/<int:pk>/', views.JobPostDetailView.as_view(), name='job_detail'),
    path('jobs/<int:job_id>/cancel/', views.cancel_job, name='job_cancel'),
    path('jobs/<int:job_id>/complete/', views.mark_job_completed, name='job_complete'),
    
    # Job Application URLs
    path('jobs/<int:job_id>/apply/', views.JobApplicationCreateView.as_view(), name='job_apply'),
    path('jobs/<int:job_id>/applications/', views.JobApplicationListView.as_view(), name='job_applications'),
    path('applications/<int:pk>/', views.JobApplicationDetailView.as_view(), name='application_detail'),
    
    # Dashboard URLs
    path('dashboard/student/', views.StudentDashboardView.as_view(), name='student_dashboard'),
    path('dashboard/teacher/', views.TeacherDashboardView.as_view(), name='teacher_dashboard'),
    
    # Review URLs
    path('jobs/<int:job_id>/review/', views.JobReviewCreateView.as_view(), name='job_review-create'),
    
    # Utility URLs
    path('jobs/<int:job_id>/schedule-meeting/', views.schedule_meeting_for_job, name='schedule_meeting'),
    path('statistics/', views.job_statistics, name='job_statistics'),
]