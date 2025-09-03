# support_feedback/views.py
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import SupportTicket, CourseFeedback, TeacherFeedback, TicketReply
from .serializers import (
    SupportTicketSerializer, SupportTicketCreateSerializer,
    CourseFeedbackSerializer, TeacherFeedbackSerializer,
    TicketReplySerializer, TicketReplyCreateSerializer
)
from authentication.models import StudentProfile,TeacherProfile

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


# Support Ticket Views
class SupportTicketListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return SupportTicketCreateSerializer
        return SupportTicketSerializer
    
    def get_queryset(self):
        return SupportTicket.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class SupportTicketDetailView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SupportTicketSerializer
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return SupportTicket.objects.none()
        return SupportTicket.objects.filter(user=self.request.user)

# Course Feedback Views
class CourseFeedbackListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CourseFeedbackSerializer
    
    def get_queryset(self):
        student_profile = StudentProfile.objects.get(user=self.request.user)
        return CourseFeedback.objects.filter(user=student_profile)
    
    def perform_create(self, serializer):
        student_profile = StudentProfile.objects.get(user=self.request.user)
        serializer.save(user=student_profile)

# Teacher Feedback Views  
class TeacherFeedbackListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TeacherFeedbackSerializer
    
    def get_queryset(self):
        return TeacherFeedback.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

# Ticket Reply View
@swagger_auto_schema(
    method='post',
    operation_summary="Add reply to a support ticket",
    manual_parameters=[
        openapi.Parameter(
            'ticket_id',
            openapi.IN_PATH,
            description="UUID of the support ticket",
            type=openapi.TYPE_INTEGER,
            required=True
        )
    ],
    request_body=TicketReplyCreateSerializer
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def add_ticket_reply(request, ticket_id):
    ticket = get_object_or_404(SupportTicket, id=ticket_id, user=request.user)
    serializer = TicketReplyCreateSerializer(data=request.data)
    
    if serializer.is_valid():
        serializer.save(ticket=ticket, user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
