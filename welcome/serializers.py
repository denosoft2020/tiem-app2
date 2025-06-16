from rest_framework import serializers
from .models import Notification, Conversation, Message, Post, Like, Comment, Profile, User
from django.contrib.auth import get_user_model
from django.conf import settings


User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'is_active', 'is_staff', 'date_joined', 'last_login', 'profile']

class NotificationSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    avatar = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = ['id', 'sender', 'notification_type', 'message', 'is_read', 'created_at', 'content_id', 'avatar']
    
    def get_avatar(self, obj):
        # This would be replaced with your actual avatar logic
        return obj.sender.username[0].upper()

class ConversationSerializer(serializers.ModelSerializer):
    participants = UserSerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = ['id', 'participants', 'created_at', 'updated_at', 'last_message', 'unread_count', 'avatar']
    
    def get_last_message(self, obj):
        last_message = obj.messages.last()
        if last_message:
            return {
                'content': last_message.content,
                'time': last_message.created_at,
                'sent': last_message.sender == self.context['request'].user
            }
        return None
    
    def get_unread_count(self, obj):
        return obj.messages.filter(is_read=False).exclude(sender=self.context['request'].user).count()
    
    def get_avatar(self, obj):
        # Get the other participant (assuming 1:1 chat)
        other_user = obj.participants.exclude(id=self.context['request'].user.id).first()
        return other_user.username[0].upper() if other_user else '?'

class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    sent = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = ['id', 'sender', 'content', 'is_read', 'created_at', 'sent']
    
    def get_sent(self, obj):
        return obj.sender == self.context['request'].user
    

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