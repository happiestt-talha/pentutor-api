from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone

from .redis_client import redis_client
from .models import Alert
from .serializers import AlertSerializer
from .utils import send_live_alert


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def heartbeat(request):
    meeting_id = request.data.get('meeting_id')
    user_id = request.user.id
    key = f"last_active:{meeting_id}:{user_id}"
    redis_client.set(key, timezone.now().isoformat())

    # 🔴 TEMPORARY: Send test alert on every heartbeat
    # Alert.objects.create(
    #     user=request.user,
    #     type="inactivity",  # just for testing
    #     message="Test alert: heartbeat received.",
    # )

    # send_live_alert(
    #     user_id=user_id,
    #     message="Test alert: heartbeat received.",
    #     alert_type="inactivity"
    # )

    return Response({"status": "active"})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_alerts(request):
    alerts = Alert.objects.filter(user=request.user).order_by('-created_at')
    serializer = AlertSerializer(alerts, many=True)
    return Response(serializer.data)