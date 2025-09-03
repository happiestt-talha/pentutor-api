# admin_dashboard/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # Admin Dashboard Overview
    path('overview/', views.admin_dashboard_overview, name='admin_dashboard_overview'),
    
    # User Management
    path('users/', views.admin_users_list, name='admin_users_list'),
    path('users/<uuid:user_id>/', views.admin_user_detail, name='admin_user_detail'),
    path('users/<uuid:user_id>/update-role/', views.admin_update_user_role, name='admin_update_user_role'),
    path('users/<uuid:user_id>/delete/', views.admin_delete_user, name='admin_delete_user'),
    
    # Teachers and Courses Management
    path('teachers-courses/', views.admin_teachers_courses, name='admin_teachers_courses'),
    
    # Course Enrollments
    path('enrollments/', views.admin_course_enrollments, name='admin_course_enrollments'),
    
    # Payment Management
    path('payments/', views.admin_course_payments, name='admin_course_payments'),
    path('payments/<int:payment_id>/verify/', views.admin_verify_payment, name='admin_verify_payment'),

    # support tickets
    path('admin/tickets/', views.AdminSupportTicketListView.as_view(), name='admin-tickets'),
    path('admin/tickets/<int:pk>/', views.AdminSupportTicketDetailView.as_view(), name='admin-ticket-detail'),
    path('admin/tickets/<int:ticket_id>/reply/', views.admin_reply_ticket, name='admin-ticket-reply'),
    path('admin/course-feedback/', views.AdminCourseFeedbackListView.as_view(), name='admin-course-feedback'),
    path('admin/teacher-feedback/', views.AdminTeacherFeedbackListView.as_view(), name='admin-teacher-feedback'),

    # pending profile lists
    path('pending-profiles/',views.admin_pending_profiles_list,name='admin_pending_profiles_list'),
    # Review profile (approve/reject)
    path('review-profile/',  views.admin_review_profile, name='admin_review_profile' ),

    path('student-queries/', views.AdminStudentQueriesView.as_view(), name='admin-student-queries'),
    path('student-queries/<int:query_id>/', views.AdminStudentQueriesView.as_view(), name='update-student-query'),

]