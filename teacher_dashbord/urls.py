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
    path('topics/<int:topic_id>/videos/',views.teacher_topic_videos, name="teacher_topic_videos"),
    
    # Quiz Management
    path('courses/<int:course_id>/quizzes/', views.teacher_course_quizzes, name='teacher_course_quizzes'),
    path('quizzes/<int:quiz_id>/', views.teacher_quiz_detail, name='teacher_quiz_detail'),
    path('topics/<int:topic_id>/quizzes/', views.teacher_topic_quizzes, name='teacher_topic_quizzes'),
    
    # Assigmenets
    path('course/<int:course_id>/assigments/',views.teacher_course_assignments,name='teacher_course_assignments'),
    path('topics/<int:topic_id>/assigments/',views.teacher_topic_assignments,name='teacher_topic_assignments'),



    # Student Management
    path('courses/<int:course_id>/students/', views.teacher_course_students, name='teacher_course_students'),
    # Add these to your existing urlpatterns
    path('courses/<int:course_id>/live-classes/', views.teacher_course_live_classes, name='teacher_course_live_classes'),
    path('live-classes/<int:class_id>/', views.teacher_live_class_detail, name='teacher_live_class_detail'),

      # Topics URLs
    path('courses/<int:course_id>/topics/', views.teacher_course_topics, name='teacher_course_topics'),
    path('topics/<int:topic_id>/', views.teacher_topic_detail, name='teacher_topic_detail'),
    path('topics/<int:topic_id>/content/', views.teacher_topic_content, name='teacher_topic_content'),
    path('courses/<int:course_id>/topics/reorder/', views.teacher_topics_reorder, name='teacher_topics_reorder'),
 
]