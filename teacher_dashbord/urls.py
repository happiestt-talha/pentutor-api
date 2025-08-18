# teacher_dashboard/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # Teacher Dashboard Overview
    path('', views.teacher_dashboard, name='teacher_dashboard'),
    
    # Course Management
    path('courses/', views.teacher_courses, name='teacher_courses'),
    path('courses/<int:course_id>/', views.teacher_course_detail, name='teacher_course_detail'),
    
    # Video Management
    path('courses/<int:course_id>/videos/', views.teacher_course_videos, name='teacher_course_videos'),
    path('videos/<int:video_id>/', views.teacher_video_detail, name='teacher_video_detail'),
    
    # Quiz Management
    path('courses/<int:course_id>/quizzes/', views.teacher_course_quizzes, name='teacher_course_quizzes'),
    path('quizzes/<int:quiz_id>/', views.teacher_quiz_detail, name='teacher_quiz_detail'),
    
    # Student Management
    path('courses/<int:course_id>/students/', views.teacher_course_students, name='teacher_course_students'),
    # Add these to your existing urlpatterns
    path('courses/<int:course_id>/live-classes/', views.teacher_course_live_classes, name='teacher_course_live_classes'),
    path('live-classes/<int:class_id>/', views.teacher_live_class_detail, name='teacher_live_class_detail'),
]