from rest_framework import serializers
from .models import Notification, ConversationRequest, Conversation, Message, Post, Like, Comment, Profile, User
from django.contrib.auth import get_user_model
from django.conf import settings
from django.urls import reverse


User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'is_active', 'is_staff', 'date_joined', 'last_login', 'profile']

class NotificationSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    avatar_url = serializers.SerializerMethodField()
    content_preview = serializers.SerializerMethodField()
    content_type = serializers.CharField(source='content_type.model', read_only=True)
    post_media_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = ['id', 'sender', 'notification_type', 'message', 'is_read', 
                  'created_at', 'avatar_url', 'content_preview', 'content_type',
                  'object_id', 'post_media_url']
    
    def get_avatar_url(self, obj):
        request = self.context.get('request')
        if obj.sender.profile.profile_picture:
            return request.build_absolute_uri(obj.sender.profile.profile_picture.url)
        return None
    
    def get_content_preview(self, obj):
        if obj.content_object and hasattr(obj.content_object, 'caption'):
            return obj.content_object.caption[:100] + '...' if len(obj.content_object.caption) > 100 else obj.content_object.caption
        return None

    def get_sender(self, obj):
        profile = getattr(obj.sender, 'profile', None)
        return {
            "username": obj.sender.username,
            "profile_picture": self.context['request'].build_absolute_uri(profile.profile_picture.url) if profile and profile.profile_picture else None
        }

    def get_post_media_url(self, obj):
        if hasattr(obj.content_object, 'media_file'):
            return self.context['request'].build_absolute_uri(obj.content_object.media_file.url)
        return None
    
class ConversationRequestSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    recipient = UserSerializer(read_only=True)
    
    class Meta:
        model = ConversationRequest
        fields = ['id', 'sender', 'recipient', 'status', 'created_at']

class ConversationSerializer(serializers.ModelSerializer):
    other_user = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    last_message_at = serializers.DateTimeField()
    unread_count = serializers.IntegerField()

    class Meta:
        model = Conversation
        fields = ['id', 'other_user', 'last_message', 'last_message_at', 'unread_count']
    
    def get_other_user(self, obj):
        request = self.context.get('request')
        other_user = obj.participants.exclude(id=request.user.id).first()
        if other_user:
            return {
                'id': other_user.id,
                'username': other_user.username,
                'profile_picture': other_user.profile.profile_picture.url if other_user.profile.profile_picture else None
            }
        return None
    
    def get_last_message(self, obj):
        return obj.last_message

class MessageSerializer(serializers.ModelSerializer):
    sender = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(format='%Y-%m-%d %H:%M')
    
    class Meta:
        model = Message
        fields = ['id', 'content', 'sender', 'created_at']
    
    def get_sender(self, obj):
        return {
            'id': obj.sender.id,
            'username': obj.sender.username
        }
   
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'profile']

class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    followers_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()
    is_following = serializers.SerializerMethodField()
    profile_picture = serializers.SerializerMethodField()
    

    class Meta:
        model = Profile
        fields = ['id', 'bio', 'profile_picture']
        read_only_fields = ['user']

    def get_profile_picture(self, obj):
       if obj.profile_picture:
            # Build absolute URL
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile_picture.url)
                
            else:
                return f"{settings.BASE_URL}{obj.profile_picture.url}"
       
       return None

    def get_followers_count(self, obj):
        return obj.followers.count()

    def get_following_count(self, obj):
        return obj.following.count()

    def get_is_following(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.followers.filter(id=request.user.profile.id).exists()
        return False

class UserProfileSerializer(serializers.ModelSerializer):
    profile_picture = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'profile_picture']
    
    def get_profile_picture(self, obj):
        if hasattr(obj, 'profile') and obj.profile.profile_picture:
            profile = obj.profile
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(profile.profile_picture.url)
            else:
                return f"{settings.BASE_DIR}{profile.profile_picture.url}"
        return None

class PostSerializer(serializers.ModelSerializer):
    user = UserProfileSerializer(read_only=True)
    likes_count = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    media_file = serializers.SerializerMethodField()
    #media_file = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = ['id', 'user', 'content_type', 'media_file', 'caption', 
                  'hashtags', 'mentions', 'location', 'created_at', 
                  'views', 'likes_count', 'comments_count', 'is_liked']
        #read_only_fields = ['user', 'views', 'created_at', 'score']

    def get_likes_count(self, obj):
        return obj.likes.count()

    def get_comments_count(self, obj):
        return obj.comments.count()

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(user=request.user).exists()
        return False

    def get_media_file(self, obj):
        request = self.context.get('request')
        if obj.media_file:
            return request.build_absolute_uri(obj.media_file.url)
        return None

class LikeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Like
        fields = '__all__'

class CommentSerializer(serializers.ModelSerializer):
    user = UserProfileSerializer(read_only=True)

    class Meta:
        model = Comment
        fields =  ['id', 'text', 'created_at', 'user']
        read_only_fields = ['user', 'created_at', 'user']