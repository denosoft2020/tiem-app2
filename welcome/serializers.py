from rest_framework import serializers
from .models import Notification, Conversation, Message
from django.contrib.auth import get_user_model

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name']

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