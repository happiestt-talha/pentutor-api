from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def send_live_alert(user_id, message, alert_type):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"user_{user_id}",
        {
            "type": "send_alert",
            "message": message,
            "type": alert_type
        }
    )