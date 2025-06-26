from django.shortcuts import render, redirect
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from rest_framework import serializers, viewsets, status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.core.files.storage import default_storage
import os
import uuid
from django.core.files.base import ContentFile
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.utils import timezone
from django_resized import ResizedImageField
from django.urls import reverse
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


#from .serializers import VideoSerializer



def user_profile_picture_path(instance, filename):
    # File will be uploaded to MEDIA_ROOT/profile_pictures/user_<id>/<filename>
    return f'profile_pictures/user_{instance.user.id}/{filename}'

def cover_photo_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/cover_photos/user_<id>/<filename>
    return f'cover_photos/user_{instance.user.id}/{filename}'



class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(max_length=500, blank=True)
    profile_picture = models.ImageField(
        upload_to='profile_pictures/',
        default='profile_pictures/default_profile.jpg'
    )
    image = models.ImageField(
        upload_to='profile_pictures/',
        default='profile_pictures/default_profile.jpg'
    )
    follows = models.ManyToManyField(
        'self',
        related_name='followed_by',
        symmetrical=False,
        blank=True
    )
    @property
    def profile_picture_url(self):
        if self.profile_picture:
            return self.profile_picture.url
        return None
    #created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user.username} Profile'

class FollowRelationship(models.Model):
    follower = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name='following_relationships'
    )
    following = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name='follower_relationships'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'following')
        ordering = ['-created_at']
        db_table = 'follow_relationships'  # Explicit table name

    def __str__(self):
        return f'{self.follower} follows {self.following}'
    

# following




@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

def user_directory_path(instance, filename):
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('uploads', filename)

# Model to store uploaded files (both images and videos)
# Django Model

class Post(models.Model):
    CONTENT_TYPES = (
        ('image', 'Image'),
        ('video', 'Video'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    content_type = models.CharField(max_length=10, choices=CONTENT_TYPES)
    media_file = models.FileField(upload_to=user_directory_path)
    caption = models.TextField(max_length=500, blank=True)
    hashtags = models.ManyToManyField('Hashtag', blank=True)
    mentions = models.ManyToManyField(User, related_name='mentioned_in', blank=True)
    location = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    views = models.PositiveIntegerField(default=0)
    score = models.FloatField(default=0)  # For algorithmic ranking

    def __str__(self):
        return f"{self.user.username} - {self.content_type}"

    def get_absolute_url(self):
        return reverse('post-detail', kwargs={'pk': self.pk})

    class Meta:
        ordering = ['-created_at']

class Like(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')

class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    text = models.TextField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}: {self.text[:20]}"

class Hashtag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    count = models.PositiveIntegerField(default=0)
    last_used = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"#{self.name}"
    
class UserInteraction(models.Model):
    INTERACTION_TYPES = (
        ('view', 'View'),
        ('like', 'Like'),
        ('comment', 'Comment'),
        ('share', 'Share'),
        ('follow', 'Follow'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, null=True, blank=True)
    target_user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='interactions_received')
    interaction_type = models.CharField(max_length=10, choices=INTERACTION_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)
    weight = models.FloatField(default=1.0)  # Weight for algorithm

    class Meta:
        indexes = [
            models.Index(fields=['user', 'interaction_type', 'timestamp']),
        ]
   

def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    instance.profile.save()

User = get_user_model()



class Following(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='following_users'
    )
    followed = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='followers'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'followed')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user} follows {self.followed}'

class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('like', 'Like'),
        ('comment', 'Comment'),
        ('reply', 'Reply'),
        ('follow', 'Follow'),
        ('mention', 'Mention'),
        ('download', 'Download'),
        ('view', 'View'),
        ('share', 'Share'),
    )
    
    recipient = models.ForeignKey(User, related_name='notifications', on_delete=models.CASCADE)
    sender = models.ForeignKey(User, related_name='sent_notifications', on_delete=models.CASCADE)
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    message = models.TextField(blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    
    # Generic foreign key for related content
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.sender} -> {self.recipient}: {self.notification_type}"
    
    def save(self, *args, **kwargs):
        # Auto-generate message based on notification type
        if not self.message:
            if self.notification_type == 'like':
                self.message = f"{self.sender.username} liked your post"
            elif self.notification_type == 'comment':
                self.message = f"{self.sender.username} commented on your post"
            elif self.notification_type == 'follow':
                self.message = f"{self.sender.username} started following you"
            elif self.notification_type == 'mention':
                self.message = f"{self.sender.username} mentioned you"
            elif self.notification_type == 'download':
                self.message = f"{self.sender.username} downloaded your content"
            elif self.notification_type == 'view':
                self.message = f"{self.sender.username} viewed your story"
            elif self.notification_type == 'share':
                self.message = f"{self.sender.username} shared your post"
        super().save(*args, **kwargs)

class Conversation(models.Model):
    participants = models.ManyToManyField(User, related_name='conversations')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

class ConversationRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    )
    
    sender = models.ForeignKey(User, related_name='sent_requests', on_delete=models.CASCADE)
    recipient = models.ForeignKey(User, related_name='received_requests', on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
   

    class Meta:
        ordering = ['-created_at']
        unique_together = ('sender', 'recipient')
    
    def __str__(self):
        return f"{self.sender} -> {self.recipient}: {self.status}"

class Message(models.Model):
    conversation = models.ForeignKey(Conversation, related_name='messages', on_delete=models.CASCADE)
    sender = models.ForeignKey(User, related_name='sent_messages', on_delete=models.CASCADE)
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)


    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.sender}: {self.content[:20]}..."
    
class LiveStream(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=80)
    channel_name = models.CharField(max_length=100, unique=True)
    viewers = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

#uploading a post from upload page
