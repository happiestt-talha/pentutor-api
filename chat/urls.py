
from django.urls import path
from . import views

urlpatterns = [
    path('chatbot/', views.ChatbotView.as_view(), name='chatbot'),
    path('<str:room_id>/', views.ChatHistoryView.as_view(), name='chat-history'),
]