from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EmailAutomationViewSet

router = DefaultRouter()
router.register(r'email-automation', EmailAutomationViewSet, basename='email-automation')

urlpatterns = [
    path('api/', include(router.urls)),
]