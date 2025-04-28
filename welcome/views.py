from django.shortcuts import render, redirect,  get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.forms import inlineformset_factory
from django.contrib.auth.forms import UserCreationForm
from django.http import JsonResponse
import json
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .models import Profile, Post, Notification, Conversation, Message, LiveStream
from .forms import ProfileUpdateForm, PostForm, ProfilePictureForm
from django.views.decorators.csrf import csrf_exempt
from django.db import models
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings
import os
import uuid
from rest_framework import viewsets, generics, permissions, status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.views import APIView
from .serializers import NotificationSerializer, ConversationSerializer, MessageSerializer
from django.contrib.auth import get_user_model
from django.db.models import Q
from agora_token_builder import RtcTokenBuilder
#from agora_token_builder.RtcTokenBuilder import Role





# Create your views here.
def welcome(request):
    return render(request, 'welcome.html')


def signin(request):
    if request.method == "POST":
        username = request.POST["username"].strip()
        email = request.POST["email"].strip()
        password = request.POST["password"].strip()
        confirmPassword = request.POST["confirmPassword"].strip()

        if password != confirmPassword:
            messages.error(request, "Passwords do not match!")
            return redirect("signin")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken!")
            return redirect("signin")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered!")
            return redirect("signin")

        user = User.objects.create_user(username=username, email=email, password=password)
        user.save()

        login(request, user)  # Log the user in after signing up
        messages.success(request, "Account created successfully!")
        return redirect("profile", username=username)  # Redirect to homepage

    return render(request, "sign-in.html")


@login_required
def home(request):
    return render(request, 'home.html')

def forgot_password(request):
    return render(request, 'forgot-password.html')


@login_required
def profile_view(request, username):
    user = get_object_or_404(User, username=username)
    profile, created = Profile.objects.get_or_create(user=user)
    if not profile.profile_picture:
        profile.profile_picture = 'profile_pictures/default.png'
        profile.save()
    
    
    try:
        profile = Profile.objects.get(user=user)
    except Profile.DoesNotExist:
        profile = Profile.objects.create(user=user)
    
    # Check if the current user is following this profile
    is_following = False
    if request.user.is_authenticated and request.user != user:
        is_following = request.user.profile.following.filter(pk=profile.pk).exists()
    
    # Get user posts
    posts = Post.objects.filter(user=user).order_by('-created_at')
    posts_count = posts.count()
    
    # Separate videos from images
    videos = posts.filter(video__isnull=False)
    images = posts.filter(image__isnull=False)
    
    # Get saved posts if viewing own profile
    saved_posts = []
    if request.user == user:
        saved_posts = request.user.saved_posts.all()
    
    context = {
        'user': user,
        'profile': profile,
        'posts_count': Post.objects.filter(user=user).count(),
        'followers_count': profile.followers.count(),
        'following_count': profile.following.count(),
        'likes_count': sum(post.likes.count() for post in Post.objects.filter(user=user)),
        'posts': Post.objects.filter(user=user).order_by('-created_at')[:9],
        'pinned_posts': Post.objects.filter(user=user, is_pinned=True),
    }
    
    return render(request, 'profile.html', context)

@login_required
@require_POST
def save_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if post.saved_by.filter(id=request.user.id).exists():
        post.saved_by.remove(request.user)
        saved = False
    else:
        post.saved_by.add(request.user)
        saved = True
    return JsonResponse({'saved': saved, 'count': post.saved_by.count()})



@login_required
@require_POST
def follow_user(request, username):
    if request.method == 'POST':
        user_to_follow = get_object_or_404(User, username=username)
        profile_to_follow = user_to_follow.profile
        current_profile = request.user.profile

        
        if request.user == user_to_follow:
            return JsonResponse({'error': 'You cannot follow yourself'}, status=400)
        
        profile_to_follow = user_to_follow.profile
        current_user_profile = request.user.profile
        
        data = json.loads(request.body)
        action = data.get('action', 'follow')
        
        if action == 'follow':
            current_user_profile.following.add(profile_to_follow)
        else:
            current_user_profile.following.remove(profile_to_follow)
        
        # Update followers count
        profile_to_follow.followers_count = profile_to_follow.followers.count()
        profile_to_follow.save()
        
        return JsonResponse({
            'status': 'success',
            'action': action,
            'followers_count': profile_to_follow.followers_count
        })
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def change_profile_picture(request):
    if request.method == 'POST':
        form = ProfilePictureForm(request.POST, request.FILES, instance=request.user.profile)
        if form.is_valid():
            form.save()
            return redirect('profile', username=request.user.username)
    else:
        form = ProfilePictureForm(instance=request.user.profile)
    
    return render(request, 'change_picture.html', {'form': form})

@login_required
def followers_list(request, username):
    user = get_object_or_404(User, username=username)
    profile = get_object_or_404(Profile, user=user)
    followers = profile.followers.all()
    return render(request, 'followers.html', {
        'profile': profile,
        'followers': followers,
        'current_tab': 'followers'
    })

@login_required
def following_list(request, username):
    user = get_object_or_404(User, username=username)
    profile = get_object_or_404(Profile, user=user)
    following = profile.following.all()
    return render(request, 'following.html', {
        'profile': profile,
        'following': following,
        'current_tab': 'following'
    })

@login_required
def my_profile(request):
    # Redirect to the profile view with the current user's username
    return redirect('profile', username=request.user.username)
    
@login_required
def edit_profile(request):
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        if form.is_valid():
            form.save()
            return redirect('profile', username=request.user.username)
    else:
        form = ProfileUpdateForm(instance=request.user.profile)
    
    return render(request, 'edit_profile.html', {'form': form})

    
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
@login_required
def upload_post(request):
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.user = request.user
            
            # Determine media type
            if request.FILES['media_file'].content_type.startswith('image'):
                post.media_type = 'image'
            elif request.FILES['media_file'].content_type.startswith('video'):
                post.media_type = 'video'
            
            post.save()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Post uploaded successfully!',
                    'username': request.user.username
                })
            return redirect('profile', username=request.user.username)
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid form data',
                    'errors': form.errors
                }, status=400)
    
    form = PostForm()
    return render(request, 'upload.html', {'form': form})


def friends(request):
    return render(request, 'friends.html')



#User = get_user_model()

class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    renderer_classes = [JSONRenderer, TemplateHTMLRenderer]  # Add TemplateHTMLRenderer
    
    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user).select_related('sender')
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        
        if request.accepted_renderer.format == 'html':
            # Return your custom template for browser requests
            return Response({'notifications': serializer.data}, template_name='notifications.html')
        
        # Return JSON for API requests
        return Response(serializer.data)

class MarkNotificationAsRead(generics.UpdateAPIView):
    queryset = Notification.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    def update(self, request, *args, **kwargs):
        notification = self.get_object()
        if notification.recipient != request.user:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        
        notification.is_read = True
        notification.save()
        return Response({"status": "marked as read"})

class ConversationListView(generics.ListAPIView):
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Conversation.objects.filter(participants=self.request.user).prefetch_related('participants', 'messages')

class ConversationCreateView(generics.CreateAPIView):
    queryset = Conversation.objects.all()
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        participants = [self.request.user]
        other_user_id = self.request.data.get('user_id')
        if other_user_id:
            try:
                other_user = User.objects.get(id=other_user_id)
                participants.append(other_user)
            except User.DoesNotExist:
                pass
        conversation = serializer.save()
        conversation.participants.set(participants)

class MessageListView(generics.ListCreateAPIView):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        conversation_id = self.kwargs['conversation_id']
        return Message.objects.filter(conversation_id=conversation_id).select_related('sender')
    
    def perform_create(self, serializer):
        conversation_id = self.kwargs['conversation_id']
        conversation = Conversation.objects.filter(
            id=conversation_id,
            participants=self.request.user
        ).first()
        
        if not conversation:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        
        message = serializer.save(
            conversation=conversation,
            sender=self.request.user
        )
        
        # Mark other user's unread messages as read when sending a new message
        Message.objects.filter(
            conversation=conversation,
            is_read=False
        ).exclude(sender=self.request.user).update(is_read=True)

class UnreadCountView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        unread_notifications = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count()
        
        unread_messages = Message.objects.filter(
            conversation__participants=request.user,
            is_read=False
        ).exclude(sender=request.user).count()
        
        return Response({
            'notifications': unread_notifications,
            'messages': unread_messages
        })
    
def feed(request):
    active_tab = request.GET.get('tab', 'reel')
    
    if active_tab == 'friends':
        # Show only posts from followed users
        following = request.user.profile.following.all()
        posts = Post.objects.filter(user__in=following).order_by('-created_at')
    else:
        # Show all posts
        posts = Post.objects.all().order_by('-created_at')
    
    return render(request, 'feed.html', {
        'posts': posts,
        'active_tab': active_tab
    })

def live(request):
    # Get users who are currently live
    live_users = Profile.objects.filter(is_live=True)
    return render(request, 'live.html', {
        'live_users': live_users,
        'active_tab': 'live'
    })

@require_POST
@login_required
def like_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if request.user in post.likes.all():
        post.likes.remove(request.user)
        liked = False
    else:
        post.likes.add(request.user)
        liked = True
    return JsonResponse({
        'success': True,
        'liked': liked,
        'likes_count': post.likes.count()
    })

@require_POST
@login_required
def follow_user(request, user_id):
    user_to_follow = get_object_or_404(User, id=user_id)
    profile = request.user.profile
    
    if user_to_follow in profile.following.all():
        profile.following.remove(user_to_follow)
        following = False
    else:
        profile.following.add(user_to_follow)
        following = True
    
    return JsonResponse({
        'success': True,
        'following': following
    })

@require_POST
@login_required
def increment_view(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    post.views += 1
    post.save()
    return JsonResponse({'success': True})

def create_stream(request):
    if request.method == 'POST':
        # Generate Agora token
        app_id = settings.AGORA_APP_ID  # Replace 'AGORA_APP_ID' with the actual attribute name in your settings
        app_certificate = settings.ee2abd03d2604699b3280f0b64e8a4cb  # Replace with the correct key or variable name
        channel_name = str(uuid.uuid4())
        user_id = request.user.id
        expiration = 3600  # 1 hour
        
        token = RtcTokenBuilder.buildTokenWithUid(
            app_id,
            app_certificate,
            channel_name,
            user_id,
            Role.PUBLISHER,
            expiration
        )
        
        # Create stream record
        stream = LiveStream.objects.create(
            user=request.user,
            title=request.POST.get('title'),
            channel_name=channel_name
        )
        
        return JsonResponse({
            'success': True,
            'token': token,
            'channel_name': channel_name
        })
    return JsonResponse({'success': False})

def end_stream(request):
    if request.method == 'POST':
        stream = LiveStream.objects.filter(user=request.user, is_active=True).first()
        if stream:
            stream.is_active = False
            stream.save()
            return JsonResponse({'success': True})
        return JsonResponse({'success': False})