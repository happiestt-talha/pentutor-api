from django.urls import path
from . import views

urlpatterns = [
    # Course listing and search
    path('', views.CourseListView.as_view(), name='course_list'),
   
    # Course detail
    path('<int:course_id>/', views.course_detail, name='course_detail'),
    path('<int:course_id>/videos/', views.course_videos, name='course_videos'),
    
    # Video detail
    path('videos/<int:video_id>/', views.video_detail, name='video_detail'),
    path('videos/<int:video_id>/quiz-assignments/', views.video_quiz_assignments, name='video_quiz_assignments'),
# for teacher
     path('teachers/', views.list_all_teachers, name='list-all-teachers'),
     path('teachers/<int:teacher_id>/', views.view_teacher_profile, name='view-teacher-profile')
    
]