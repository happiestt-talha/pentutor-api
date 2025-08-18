from django.urls import path
from .views import user_alerts, heartbeat

urlpatterns = [
    path('', user_alerts, name='user-alerts'),
    path('heartbeat/', heartbeat, name='heartbeat'),
]