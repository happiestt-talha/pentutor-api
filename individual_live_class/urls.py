# live_classes/urls.py

from django.urls import path
from . import views

app_name = 'live_classes'

urlpatterns = [
    # Teacher URLs
    path('teacher/schedules/', views.TeacherScheduleListView.as_view(), name='teacher_schedules'),
    path('teacher/create-schedule/', views.CreateLiveClassScheduleView.as_view(), name='create_schedule'),
    path('teacher/schedules/<uuid:schedule_id>/update/', views.UpdateLiveClassScheduleView.as_view(), name='update_schedule'),
     path('teacher/schedules/<uuid:id>/reschedule/', views.RescheduleMeetingView.as_view(), name='reschedule-meeting'),
    
    # Student URLs
    path('student/schedules/', views.StudentScheduleListView.as_view(), name='student_schedules'),
    path('student/subscriptions/', views.StudentSubscriptionListView.as_view(), name='student_subscriptions'),
    path('student/subscribe/', views.CreateSubscriptionView.as_view(), name='create_subscription'),
    
    # Session Management
    path('sessions/', views.SessionListView.as_view(), name='session_list'),
    path('join/<uuid:schedule_id>/', views.join_live_class, name='join_class'),
    path('end/<uuid:session_id>/', views.end_live_class, name='end_class'),
    
    # Reschedule Management
    path('reschedule/request/', views.RescheduleRequestView.as_view(), name='reschedule_request'),
    path('reschedule/pending/', views.PendingReschedulesView.as_view(), name='pending_reschedules'),
    path('reschedule/<int:reschedule_id>/approve/', views.approve_reschedule, name='approve_reschedule'),
    
    # Admin URLs
    path('admin/schedules/', views.AdminScheduleListView.as_view(), name='admin_schedules'),
    path('admin/payments/', views.AdminPaymentListView.as_view(), name='admin_payments'),
    path('admin/sessions/', views.AdminSessionListView.as_view(), name='admin_sessions'),
    
    # Analytics & Utility
    path('schedule/<uuid:schedule_id>/analytics/', views.schedule_analytics, name='schedule_analytics'),
    path('upcoming/', views.upcoming_classes, name='upcoming_classes'),
]