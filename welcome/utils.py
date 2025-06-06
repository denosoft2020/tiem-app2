# utils.py
from django.contrib.auth import get_user_model
from .models import Notification, UserInteraction, Profile, Post
from django.db.models import Count, Q, F, ExpressionWrapper, FloatField
from django.utils import timezone
from datetime import timedelta
from .serializers import NotificationSerializer


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


def calculate_post_score(post, user):
    """Calculate personalized score for a post based on user interactions"""
    base_score = 0.0
    
    # Content popularity factors
    popularity = (
        0.4 * min(post.views / 1000, 1.0) +
        0.3 * min(post.likes.count() / 100, 1.0) +
        0.2 * min(post.comments.count() / 50, 1.0) +
        0.1 * min(post.created_at.timestamp() / timezone.now().timestamp(), 1.0)
    )
    
    # User-specific factors
    user_factor = 0.0
    if user.is_authenticated:
        # Relationship with poster
        if user == post.user:
            user_factor += 0.5  # Own content
        elif Profile.objects.filter(user=user, following__user=post.user).exists():
            user_factor += 0.4  # Following
        
        # Recent interactions with similar content
        recent_interactions = UserInteraction.objects.filter(
            user=user,
            timestamp__gte=timezone.now() - timedelta(days=7)
        ).values('interaction_type').annotate(count=Count('id'))
        
        for interaction in recent_interactions:
            if interaction['interaction_type'] == 'like':
                user_factor += 0.2 * min(interaction['count'] / 10, 1.0)
            elif interaction['interaction_type'] == 'comment':
                user_factor += 0.3 * min(interaction['count'] / 5, 1.0)
            elif interaction['interaction_type'] == 'share':
                user_factor += 0.5 * min(interaction['count'] / 3, 1.0)
    
    # Combine scores with weights
    score = (0.7 * popularity) + (0.3 * user_factor)
    return round(score, 4)

def get_feed_posts(user, tab='reel', page=1, per_page=10):
    """Get personalized feed posts based on algorithm"""
    # Base queryset
    posts = Post.objects.annotate(
        popularity_score=ExpressionWrapper(
            0.4 * F('views') / 1000 +
            0.3 * Count('likes') / 100 +
            0.2 * Count('comments') / 50,
            output_field=FloatField()
        )
    ).select_related('user').prefetch_related('likes', 'comments')
    
    # Filter based on tab
    if tab == 'following' and user.is_authenticated:
        following_ids = Profile.objects.filter(
            user__in=user.Profile.following.all()
        ).values_list('user_id', flat=True)
        posts = posts.filter(user_id__in=following_ids)
    elif tab == 'live':
        # Placeholder for live content
        posts = posts.filter(content_type='video')[:per_page]
        return posts
    
    # Calculate personalized scores
    for post in posts:
        post.score = calculate_post_score(post, user)
    
    # Sort by score (descending) and recency
    sorted_posts = sorted(
        posts, 
        key=lambda p: (p.score, p.created_at), 
        reverse=True
    )
    
    # Pagination
    start = (page - 1) * per_page
    end = start + per_page
    return sorted_posts[start:end]