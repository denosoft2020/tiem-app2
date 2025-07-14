from rest_framework import serializers
from .models import Notification, ConversationRequest, Conversation, Message, Post, Like, Comment, Profile, User
from django.contrib.auth import get_user_model
from django.conf import settings
from django.urls import reverse


User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    profile_picture = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'is_active', 'is_staff', 'date_joined', 'last_login', 'profile', 'profile_picture']

    def get_profile_picture(self, obj):
        if obj.profile.profile_picture:
            return obj.profile.profile_picture.url
        return None

class NotificationSerializer(serializers.ModelSerializer):
    post_id = serializers.SerializerMethodField()
    post_thumbnail_url = serializers.SerializerMethodField()
    sender = serializers.SerializerMethodField()

    def get_sender(self, obj):
        profile = getattr(obj.sender, 'profile', None)
        request = self.context.get('request')
        pic = profile.profile_picture.url if profile and profile.profile_picture else None
        return {
            'id': obj.sender.id,
            'username': obj.sender.username,
            'profile_picture': request.build_absolute_uri(pic) if pic else None
        }

    def get_post_id(self, obj):
        post = getattr(obj, 'content_object', None)
        return post.id if post else None

    def get_post_thumbnail_url(self, obj):
        post = getattr(obj, 'content_object', None)
        if post and hasattr(post, 'media_file') and post.media_file:
            request = self.context.get('request')
            return request.build_absolute_uri(post.media_file.url)
        return None

    class Meta:
        model = Notification
        fields = [
            'id', 'sender', 'message', 'notification_type',
            'created_at', 'is_read',
            'post_id', 'post_thumbnail_url'
        ]


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
    is_following = serializers.SerializerMethodField()
    hashtags = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field='name'
    )
    mentions = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field='username'
    )


    class Meta:
        model = Post
        fields = ['id', 'user', 'content_type', 'media_file', 'caption', 
                  'hashtags', 'mentions', 'location', 'created_at', 
                  'views', 'likes_count', 'comments_count', 'is_liked', 'is_following']
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
    
    def get_is_following(self, obj):
        user = self.context['request'].user
        if user.is_authenticated:
            return user.profile.follows.filter(id=obj.user.id).exists()
        return False

class LikeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Like
        fields = '__all__'

class ReplySerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()

    class Meta:
        model = Comment
        fields = ['id', 'user', 'text', 'created_at']

class CommentSerializer(serializers.ModelSerializer):
    user = UserProfileSerializer(read_only=True)
    parent = serializers.PrimaryKeyRelatedField(read_only=True)
    replies = ReplySerializer(many=True, read_only=True)
    likes_count = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields =  ['id', 'text', 'created_at', 'user', 'parent', 'replies', 'post', 'likes_count']
        read_only_fields = ['user', 'post']
        
    def get_replies(self, obj):
        # Recursively serialize replies
        replies = obj.replies.all()
        return CommentSerializer(replies, many=True).data
    
    def get_likes_count(self, obj):
        return obj.likes.count()
    


