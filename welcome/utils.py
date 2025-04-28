# utils.py
from django.contrib.auth import get_user_model
from .models import Notification

User = get_user_model()

def create_notification(recipient, sender, notification_type, message='', content_id=None):
    """
    Create a notification for a user
    """
    notification = Notification.objects.create(
        recipient=recipient,
        sender=sender,
        notification_type=notification_type,
        message=message,
        content_id=content_id
    )
    
    # Send real-time update via WebSocket
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'user_{recipient.id}',
        {
            'type': 'send_notification',
            'content': {
                'type': 'notification',
                'data': NotificationSerializer(notification).data
            }
        }
    )
    
    return notification