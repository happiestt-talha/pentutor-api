# support_feedback/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Student/User endpoints
    path('tickets/', views.SupportTicketListCreateView.as_view(), name='support-tickets'),
    path('tickets/<int:pk>/', views.SupportTicketDetailView.as_view(), name='support-ticket-detail'),
    path('tickets/<int:ticket_id>/reply/', views.add_ticket_reply, name='ticket-reply'),
    
    path('course-feedback/', views.CourseFeedbackListCreateView.as_view(), name='course-feedback'),
    path('teacher-feedback/', views.TeacherFeedbackListCreateView.as_view(), name='teacher-feedback'),
    
  
]