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
from django.core.files.base import ContentFile
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.utils import timezone
from django_resized import ResizedImageField

#from .serializers import VideoSerializer



def user_profile_picture_path(instance, filename):
    # File will be uploaded to MEDIA_ROOT/profile_pictures/user_<id>/<filename>
    return f'profile_pictures/user_{instance.user.id}/{filename}'

def cover_photo_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/cover_photos/user_<id>/<filename>
    return f'cover_photos/user_{instance.user.id}/{filename}'

#model to the profile page
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    profile_picture = models.ImageField(
        upload_to=user_profile_picture_path,
        default='profile_pictures/default_profile.jpg'
    )
    cover_photo = models.ImageField(upload_to='profiles/covers/', blank=True, null=True)
    followers_count = models.PositiveIntegerField(default=0)
    following_count = models.PositiveIntegerField(default=0)
    profile_picture = models.ImageField(
        upload_to=user_profile_picture_path,  # Use the defined function
        default='profile_pictures/default.jpg'
    )
    followers = models.ManyToManyField(
        'self',
        related_name='following',
        symmetrical=False,
        blank=True
    )

    @property
    def followers_count(self):
        return self.followers.count()

    @property
    def following_count(self):
        return self.following.count()

    cover_photo = models.ImageField(
        upload_to=cover_photo_path,
        blank=True,
        null=True
    )

    image = ResizedImageField(
        size=[400, 400],
        crop=['middle', 'center'],
        quality=85,
        upload_to='profile_pics/',
        blank=True,
        null=True
    )

    def __str__(self):
        return self.user.username

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

# Model to store uploaded files (both images and videos)
# Django Model

class Post(models.Model):
    MEDIA_TYPE_CHOICES = [
        ('image', 'Image'),
        ('video', 'Video'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)  # Who posted it
    media_type = models.CharField(max_length=5, choices=MEDIA_TYPE_CHOICES)
    media_file = models.FileField(upload_to='posts/')
    caption = models.TextField(blank=True)  # Optional caption
    filter_effect = models.CharField(max_length=50, blank=True)
    duration = models.PositiveIntegerField(default=15)  # in seconds
    video = models.FileField(upload_to="uploads/videos/", blank=True, null=True)  # Video uploads
    image = models.ImageField(upload_to="uploads/images/", blank=True, null=True)  # Image uploads
    created_at = models.DateTimeField(auto_now_add=True)  # Timestamp
    saved_by = models.ManyToManyField(User, related_name='saved_posts', blank=True)
    likes = models.ManyToManyField(User, related_name='liked_posts', blank=True)
    is_pinned = models.BooleanField(default=False)

    @property
    def like_count(self):
        return self.likes.count()


    def __str__(self):
        return f"Post by {self.user.username} at {self.created_at}"

def user_profile_picture_path(instance, filename):
    # File will be uploaded to MEDIA_ROOT/profile_pictures/user_<id>/<filename>
    return f'profile_pictures/user_{instance.user.id}/{filename}'


def cover_photo_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/cover_photos/user_<id>/<filename>
    return f'cover_photos/user_{instance.user.id}/{filename}'


def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    instance.profile.save()

User = get_user_model()

class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('like', 'Like'),
        ('comment', 'Comment'),
        ('reply', 'Reply'),
        ('follow', 'Follow'),
    )
    
    recipient = models.ForeignKey(User, related_name='notifications', on_delete=models.CASCADE)
    sender = models.ForeignKey(User, related_name='sent_notifications', on_delete=models.CASCADE)
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    content_id = models.PositiveIntegerField(null=True, blank=True)  # ID of related content
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.sender} -> {self.recipient}: {self.notification_type}"

class Conversation(models.Model):
    participants = models.ManyToManyField(User, related_name='conversations')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"Conversation {self.id}"

class Message(models.Model):
    conversation = models.ForeignKey(Conversation, related_name='messages', on_delete=models.CASCADE)
    sender = models.ForeignKey(User, related_name='sent_messages', on_delete=models.CASCADE)
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    
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