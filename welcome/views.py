from decimal import ROUND_HALF_EVEN
from django.shortcuts import render, redirect,  get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.forms import inlineformset_factory
from django.contrib.auth.forms import UserCreationForm
from django.http import JsonResponse, HttpResponse
import json
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .models import Profile, Post, Notification, Conversation, Message, LiveStream, UserInteraction, Hashtag, Like, Comment, User 
from .forms import ProfileUpdateForm, ProfilePictureForm
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import cache_page
from django.db import models
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.conf import settings
import os
import uuid
from rest_framework import viewsets, generics, permissions, status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.views import APIView
from rest_framework.decorators import api_view, action, permission_classes
from rest_framework.permissions import IsAuthenticated
from .serializers import NotificationSerializer, ConversationSerializer, MessageSerializer
from django.contrib.auth import get_user_model
from django.db.models import Q
from agora_token_builder import RtcTokenBuilder
from .serializers import (
    PostSerializer, 
    LikeSerializer, 
    CommentSerializer, 
    ProfileSerializer,
    UserSerializer
)
from .utils import get_feed_posts
import re
import logging
logger = logging.getLogger(__name__)
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
@login_required
def profile_view(request, username):
    user = get_object_or_404(User, username=username)
    profile = get_object_or_404(Profile, user=user)
    
    # Handle default profile picture
    if not profile.profile_picture:
        profile.profile_picture = 'profile_pictures/default_profile.jpg'
        profile.save()
    
    # Get user posts
    posts = Post.objects.filter(user=user).order_by('-created_at')
    
    context = {
        'user': user,
        'profile': profile,
        'profile_picture': profile.profile_picture.url if profile.profile_picture else None,
        'posts_count': posts.count(),
        'followers_count': profile.followed_by.count(),
        'following_count': profile.follows.count(),
        'likes_count': Like.objects.filter(post__user=user).count(),
        'posts': posts[:12],  # Limit to 12 posts
    }
    
    return render(request, 'profile.html', context)


@api_view(['POST'])
@login_required
def api_follow_user(request, user_id):
    user_to_follow = get_object_or_404(User, id=user_id)
    profile = request.user.profile
    profile_to_follow = user_to_follow.profile
    
    if request.user == user_to_follow:
        return Response({'error': 'Cannot follow yourself'}, status=400)
    
    data = request.data
    action = data.get('action', 'follow')
    
    if action == 'follow':
        profile.follows.add(profile_to_follow)
    else:
        profile.follows.remove(profile_to_follow)
    
    return Response({
        'isFollowing': action == 'follow',
        'followers_count': profile_to_follow.followed_by.count()
    })

class ProfileViewSet(viewsets.ModelViewSet):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    @action(detail=True, methods=['post'])
    def follow(self, request, pk=None):
        profile = self.get_object()
        user_profile = request.user.profile
        
        if user_profile == profile:
            return Response(
                {"error": "Cannot follow yourself"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if user_profile.following.filter(id=profile.id).exists():
            user_profile.following.remove(profile)
            action = 'unfollow'
        else:
            user_profile.following.add(profile)
            action = 'follow'
            
            # Record interaction
            UserInteraction.objects.create(
                user=request.user,
                target_user=profile.user,
                interaction_type='follow'
            )
        
        return Response({"action": action}, status=status.HTTP_200_OK)

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

class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        post = serializer.save(user=self.request.user)
        
        # Process hashtags
        hashtags = re.findall(r"#(\w+)", post.caption)
        for tag in hashtags:
            hashtag, created = Hashtag.objects.get_or_create(name=tag.lower())
            hashtag.count += 1
            hashtag.save()
            post.hashtags.add(hashtag)
        
        # Process mentions
        mentions = re.findall(r"@(\w+)", post.caption)
        for username in mentions:
            try:
                user = User.objects.get(username=username)
                post.mentions.add(user)
            except User.DoesNotExist:
                pass

    @action(detail=True, methods=['post'])
    def like(self, request, pk=None):
        post = self.get_object()
        like, created = Like.objects.get_or_create(
            user=request.user, 
            post=post
        )
        
        if not created:
            like.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        
        # Record interaction
        UserInteraction.objects.create(
            user=request.user,
            post=post,
            interaction_type='like'
        )
        return Response(status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def increment_views(self, request, pk=None):
        post = self.get_object()
        post.views += 1
        post.save()
        
        # Record interaction
        UserInteraction.objects.create(
            user=request.user,
            post=post,
            interaction_type='view'
        )
        return Response(status=status.HTTP_200_OK)
    
class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        comment = serializer.save(user=self.request.user)
        
        # Record interaction
        UserInteraction.objects.create(
            user=self.request.user,
            post=comment.post,
            interaction_type='comment'
        )


def upload_page(request):
    """Renders the camera UI page"""
    return render(request, 'upload.html')

@require_POST
@login_required
def upload_media(request):
    try:
        # Verify file exists in request
        if 'file' not in request.FILES:
            return JsonResponse({'status': 'error', 'message': 'No file provided'}, status=400)
        
        uploaded_file = request.FILES['file']
        file_type = request.POST.get('file_type', 'image')
        caption = request.POST.get('caption', '')
        hashtags = request.POST.get('hashtags', '')
        mentions = request.POST.get('mentions', '')
        location = request.POST.get('location', '')

        # Determine content type based on file MIME type
        if uploaded_file.content_type.startswith('video/'):
            content_type = 'video'
        elif uploaded_file.content_type.startswith('image/'):
            content_type = 'image'
        else:
            content_type = file_type  # Fallback to provided type

         # Create the Post object
        post = Post.objects.create(
            user=request.user,
            content_type=content_type,
            media_file=uploaded_file,
            caption=caption,
            location=location
        )
         # Process hashtags
        for tag in hashtags.split():
            if tag.startswith('#'):
                tag = tag[1:]
            if tag:
                hashtag, created = Hashtag.objects.get_or_create(name=tag.lower())
                post.hashtags.add(hashtag)

        # Process mentions
        for username in mentions.split():
            if username.startswith('@'):
                username = username[1:]
            if username:
                try:
                    user = User.objects.get(username=username)
                    post.mentions.add(user)
                except User.DoesNotExist:
                    pass


        return JsonResponse({
            'status': 'success',
            'message': 'Post created successfully',
            'post_id': post.id,
            
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

#for mentions and hashtags on upload page
def get_users(request):
    users = User.objects.all().values('id', 'username')
    return JsonResponse(list(users), safe=False)
#for mentions and hashtags on upload page
@cache_page(60 * 15)  # Cache for 15 minutes
def get_users(request):
    users = User.objects.all().values('id', 'username')
    return JsonResponse(list(users), safe=False)
# views.py
@cache_page(60 * 15)
def get_hashtags(request):
    query = request.GET.get('q', '')
    # Return filtered hashtags from your database
    return JsonResponse([], safe=False)

@cache_page(60 * 15)
def search_users(request):
    query = request.GET.get('q', '')
    users = User.objects.filter(username__icontains=query).values('username')
    return JsonResponse(list(users), safe=False)


from rest_framework.pagination import PageNumberPagination

class FeedPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })

class FeedViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = FeedPagination
    
    def list(self, request):
        tab = request.query_params.get('tab', 'reel')
        page = int(request.query_params.get('page', 1))
        
        if tab == 'reel':
            # Show all posts ordered by creation date
            posts = Post.objects.all().order_by('-created_at')
        elif tab == 'following':
            # Show posts from followed users
            following = request.user.profile.follows.all()
            followed_users = [profile.user for profile in following]
            posts = Post.objects.filter(user__profile__in=following).order_by('-created_at')
        elif tab == 'live':
            # Show live streams (we'll implement this later)
            posts = Post.objects.none()  # Empty for now
        
        #prefetch related data to optimize queries
        posts = posts.select_related('user__profile').prefetch_related('likes', 'comments')    
        paginator = self.pagination_class()
        page_data = paginator.paginate_queryset(posts, request)
        
        serializer = PostSerializer(page_data, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)

def friends(request):
    return render(request, 'friends.html')

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def comprehensive_search(request):
    try:
        query = request.GET.get('q', '').strip()
        type_param = request.GET.get('type', 'all').lower()
        
        if not query:
            return JsonResponse({
                'users': [],
                'videos': [],
                'images': [],
                'hashtags': []
            })
        
        results = {
            'users': [],
            'videos': [],
            'images': [],
            'hashtags': []
        }
        
        # Define limits
        limit_per_type = 5  # when type is 'all'
        if type_param != 'all':
            limit_per_type = 20
        
        # Search Users - Fixed to use username only
        if type_param in ['all', 'users']:
            users = User.objects.filter(
                username__icontains=query
            ).distinct().select_related('profile')[:limit_per_type]
            
            for user in users:
                profile = getattr(user, 'profile', None)
                profile_picture_url = profile.profile_picture.url if profile and profile.profile_picture else None
                
                results['users'].append({
                    'id': user.id,
                    'username': user.username,
                    'profile_picture': request.build_absolute_uri(profile_picture_url) if profile_picture_url else None
                })
        
        # Search Videos - Fixed content_type filter
        if type_param in ['all', 'videos']:
            videos = Post.objects.filter(
                content_type='video',
                caption__icontains=query
            ).distinct().select_related('user')[:limit_per_type]
            
            for video in videos:
                media_url = video.media_file.url if video.media_file else None
                results['videos'].append({
                    'id': video.id,
                    'caption': video.caption,
                    'user': video.user.username,
                    'media_url': request.build_absolute_uri(media_url) if media_url else None
                })
        
        # Search Images - Fixed content_type filter
        if type_param in ['all', 'images']:
            images = Post.objects.filter(
                content_type='image',
                caption__icontains=query
            ).distinct().select_related('user')[:limit_per_type]
            
            for image in images:
                media_url = image.media_file.url if image.media_file else None
                results['images'].append({
                    'id': image.id,
                    'caption': image.caption,
                    'user': image.user.username,
                    'media_url': request.build_absolute_uri(media_url) if media_url else None
                })
        
        # Search Hashtags
        if type_param in ['all', 'hashtags']:
            hashtags = Hashtag.objects.filter(name__icontains=query).distinct()[:limit_per_type]
            
            for hashtag in hashtags:
                results['hashtags'].append({
                    'id': hashtag.id,
                    'name': hashtag.name,
                    'count': hashtag.count
                })
        
        return JsonResponse(results)
    
    except Exception as e:
        logger.exception("Error in comprehensive_search")
        return JsonResponse({'error': str(e)}, status=500)



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

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_view(request):
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse([], safe=False)
    
    # Search users by username or full name
    users = User.objects.filter(
        Q(username__icontains=query) | 
        Q(Profile__full_name__icontains=query)
    ).select_related('Profile')[:20]  # Limit results
    
    results = []
    for user in users:
        results.append({
            'username': user.username,
            'full_name': user.Profile.full_name if hasattr(user, 'Profile') else '',
            'profile_picture': user.Profile.profile_picture.url if hasattr(user, 'Profile') and user.Profile.profile_picture else None
        })
    
    return JsonResponse(results, safe=False)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_media(request, post_id):
    try:
        post = Post.objects.get(id=post_id)
        if not post.media_file:
            return HttpResponse('File not found', status=404)
        
        # Check if user has permission to download
        if not (post.user == request.user or post.is_public):
            return HttpResponse('Permission denied', status=403)
        
        file_path = post.media_file.path
        if not os.path.exists(file_path):
            return HttpResponse('File not found', status=404)
        
        with open(file_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type='application/octet-stream')
            response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
            return response
            
    except Post.DoesNotExist:
        return HttpResponse('Post not found', status=404)


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
    like, created = Like.objects.get_or_create(
        user=request.user, 
        post=post
    )
    
    if not created:
        like.delete()
        liked = False
    else:
        # Record interaction
        UserInteraction.objects.create(
            user=request.user,
            post=post,
            interaction_type='like'
        )
        liked = True
    
    return JsonResponse({
        'success': True,
        'liked': liked,
        'likes_count': post.likes.count()
    })


@api_view(['GET', 'POST'])
@login_required
def post_comments(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    
    if request.method == 'GET':
        comments = Comment.objects.filter(post=post).select_related('user')
        serializer = CommentSerializer(comments, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        # Extract text from request data
        text = request.data.get('text')
        if not text or text.strip() == '':
            return Response({"error": "Comment text is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Create the comment
        comment = Comment.objects.create(
            text=text.strip(),
            user=request.user,
            post=post
        )
        
        # Record interaction
        UserInteraction.objects.create(
            user=request.user,
            post=post,
            interaction_type='comment'
        )
        
        # Update comment count on post
        post.comments_count = Comment.objects.filter(post=post).count()
        post.save()
        
        serializer = CommentSerializer(comment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

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



def create_stream(request):
    if request.method == 'POST':
        # Generate Agora token
        app_id = settings.AGORA_APP_ID  # Replace 'AGORA_APP_ID' with the actual attribute name in your settings
        app_certificate = settings.AGORA_APP_CERTIFICATE  # Replace with the correct key or variable name
        channel_name = str(uuid.uuid4())
        user_id = request.user.id
        expiration = 3600  # 1 hour
        
        token = RtcTokenBuilder.buildTokenWithUid(
            app_id,
            app_certificate,
            channel_name,
            user_id,
            RtcTokenBuilder.PUBLISHER,
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