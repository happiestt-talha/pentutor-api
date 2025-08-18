# student_dashboard/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # Dashboard overview
    path('', views.student_dashboard, name='student_dashboard'),
    
    # Courses
    path('courses/', views.student_enrolled_courses, name='student_enrolled_courses'),
    path('courses/available/', views.available_courses, name='available_courses'),
    path('courses/<int:course_id>/enroll/', views.enroll_in_course, name='enroll_in_course'),
    path('courses/<int:course_id>/progress/', views.student_course_progress, name='student_course_progress'),
    
    # Progress tracking
    path('videos/<int:video_id>/complete/', views.mark_video_completed, name='mark_video_completed'),
    path('quizzes/<int:quiz_id>/complete/', views.mark_quiz_completed, name='mark_quiz_completed'),
    
    # Payment history
    path('payments/', views.student_payment_history, name='student_payment_history'),
]