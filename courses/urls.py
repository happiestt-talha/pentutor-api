from django.urls import path
from . import views

urlpatterns = [
    # Course listing and search
    path('', views.CourseListView.as_view(), name='course_list'),
   
    # Course detail
    path('<int:course_id>/', views.course_detail, name='course_detail'),
    path('<int:course_id>/videos/', views.course_videos, name='course_videos'),
    path('<int:course_id>/topics/', views.course_topics, name='course_topics'),

    # Topics detail 
    path('topics/<int:topic_id>/', views.topic_detail, name='topics'),
    path('topics/<int:topic_id>/videos/', views.topic_videos, name='topics_videos'),
    
    # Video detail
    path('videos/<int:video_id>/', views.video_detail, name='video_detail'),
    path('videos/<int:video_id>/deatil/', views.video_detail_with_topic, name='video_topics_detail'),
    path('videos/<int:video_id>/quiz-assignments/', views.video_quiz_assignments, name='video_quiz_assignments'),
# for teacher
     path('teachers/', views.list_all_teachers, name='list-all-teachers'),
     path('teachers/<int:teacher_id>/', views.view_teacher_profile, name='view-teacher-profile')
    
]