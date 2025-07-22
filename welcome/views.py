from decimal import ROUND_HALF_EVEN
from django.shortcuts import render, redirect,  get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib import messages
from django.forms import inlineformset_factory
from django.contrib.auth.forms import UserCreationForm
from django.http import JsonResponse, HttpResponse
import json
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_http_methods
from django.utils.decorators import method_decorator
from .models import Profile, Post, Notification, Message, LiveStream, UserInteraction, Hashtag, Like, Comment, User, ConversationRequest, Conversation
from .forms import ProfileUpdateForm, ProfilePictureForm, EmailChangeForm, CustomPasswordChangeForm, PrivacySettingsForm, SupportForm
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import cache_page
from django.db import models
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.conf import settings
from django.urls import reverse, reverse_lazy
from django.views.generic import DetailView, DeleteView, TemplateView
from django.contrib.auth.views import LogoutView
import os
import uuid
from rest_framework import viewsets, generics, permissions, status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.views import APIView
from rest_framework.decorators import api_view, action, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework import serializers
from .serializers import NotificationSerializer, MessageSerializer, ConversationRequestSerializer, ConversationSerializer
from django.contrib.auth import get_user_model
from django.db.models import Q, Count, Subquery, OuterRef, Max, Prefetch, Exists
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

        terms_accepted = request.POST.get('acceptLicense') == 'on'
        if not terms_accepted:
            messages.error(request, "You must accept the terms and conditions")
            return redirect("signin")

        if password != confirmPassword:
            messages.error(request, "Passwords do not match!")
            return redirect("signin")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken!")
            return redirect("signin")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered!")
            return redirect("signin")

        user = User(username=username, email=email)
        user.set_password(password)
        user.save() 

         # Check if profile was created
        if not hasattr(user, 'profile'):
            Profile.objects.create(user=user)

        login(request, user)  # Log the user in after signing up
        messages.success(request, "Account created successfully!")
        return redirect("profile", username=username)  # Redirect to homepage

    return render(request, "sign-in.html")

@csrf_exempt
def api_login(request):
    if request.method == "POST":
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')

        user = authenticate(username=username, password=password)
        if user:
            return JsonResponse({'message': 'Login successful'})
        else:
            return JsonResponse({'error': 'Invalid credentials'}, status=400)
    return JsonResponse({'error': 'Invalid method'}, status=405)

def terms_and_conditions(request):
    return render(request, 'terms.html')

@login_required
def home(request):
    return render(request, 'home.html')

def forgot_password(request):
    return render(request, 'forgot-password.html')

@login_required
def profile_view(request, username):
    user = get_object_or_404(User, username=username)
    profile = get_object_or_404(Profile, user=user)
     # Check if current user is following this profile
    is_following = False
    if request.user.is_authenticated:
        is_following = request.user.profile.follows.filter(id=profile.id).exists()

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
        'is_following': is_following,
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

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def follow_toggle(request, username):
    try:
        target_user = User.objects.get(username=username)
        target_profile = target_user.profile
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)

    user_profile = request.user.profile

    if user_profile == target_profile:
        return Response({'error': 'You cannot follow yourself'}, status=400)

    if target_profile in user_profile.follows.all():
        user_profile.follows.remove(target_profile)
        status_result = 'unfollowed'
    else:
        user_profile.follows.add(target_profile)
        status_result = 'followed'

    return Response({'status': status_result})
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

    @action(detail=True, methods=['post'], permission_classes=[permissions.AllowAny])
    def increment_views(self, request, pk=None):
        post = self.get_object()
        post.views += 1
        post.save()
        return Response({"views": post.views}, status=200)

        
        # Record interaction
        UserInteraction.objects.create(
            user=request.user,
            post=post,
            interaction_type='view'
        )
        return Response(status=status.HTTP_200_OK)
    

@login_required
def account_settings(request):
    email_form = EmailChangeForm(instance=request.user)
    password_form = CustomPasswordChangeForm(user=request.user)
    success_message = None

    if request.method == 'POST':
        if 'email_submit' in request.POST:
            email_form = EmailChangeForm(request.POST, instance=request.user)
            if email_form.is_valid():
                email_form.save()
                messages.success(request, 'Email updated successfully!')
                return redirect('account_settings')
                
        elif 'password_submit' in request.POST:
            password_form = CustomPasswordChangeForm(user=request.user, data=request.POST)
            if password_form.is_valid():
                try:
                    user = password_form.save()
                    update_session_auth_hash(request, user)
                    messages.success(request, 'Password updated successfully!')
                    return redirect('account_settings')
                except Exception as e:
                    messages.error(request, f'Error updating password: {str(e)}')


    
    context = {
        'email_form': email_form,
        'password_form': password_form
    }
    return render(request, 'account_settings.html', context)

@login_required
def privacy_settings(request):
    profile = request.user.profile
    form = PrivacySettingsForm(instance=profile)
    
    if request.method == 'POST':
        form = PrivacySettingsForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Privacy settings updated!')
            return redirect('privacy_settings')
    
    return render(request, 'privacy_settings.html', {'form': form})

@login_required
def help_center(request):
    form = SupportForm()
    
    if request.method == 'POST':
        form = SupportForm(request.POST)
        if form.is_valid():
            # Process support request (send email/save to DB)
            messages.success(request, 'Your message has been sent to support!')
            return redirect('help_center')
    
    return render(request, 'help_center.html', {'form': form})

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_post(request, post_id):
    try:
        post = Post.objects.get(id=post_id)
        if request.user != post.user:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        # Delete associated media file from storage
        if post.media_file:
            file_path = post.media_file.path
            if default_storage.exists(file_path):
                default_storage.delete(file_path)
        
        post.delete()
        return Response({'success': True}, status=status.HTTP_200_OK)
    except Post.DoesNotExist:
        return Response({'error': 'Post not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error deleting post: {str(e)}")
        return Response({'error': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@require_http_methods(["POST", "GET"])
def custom_logout(request):
    logout(request)
    return redirect('/')

class CommentListCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get(self, request, post_id):
        comments = Comment.objects.filter(post_id=post_id, parent__isnull=True).order_by('-created_at')
        serializer = CommentSerializer(comments, many=True)
        return Response(serializer.data)

    def post(self, request, post_id):
        post = Post.objects.get(id=post_id)
        data = request.data.copy()
        data['post'] = post.id
        data['user'] = request.user.id

        serializer = CommentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user, post=post)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class CommentReplyListAPIView(generics.ListAPIView):
    serializer_class = CommentSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        comment_id = self.kwargs.get('comment_id')
        return Comment.objects.filter(parent_id=comment_id).order_by('created_at')

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

# nested comments and feed view

class PostCommentsAPIView(APIView):
    def get(self, request, post_id):
        try:
            post = Post.objects.get(id=post_id)
            # Get top-level comments and prefetch replies
            comments = Comment.objects.filter(
                post=post, 
                parent__isnull=True
            ).prefetch_related(
                'replies',
                'replies__user',
                'replies__user__profile'
            )
            
            serializer = CommentSerializer(comments, many=True)
            return Response(serializer.data)
        except Post.DoesNotExist:
            return Response(
                {"error": "Post not found"},
                status=status.HTTP_404_NOT_FOUND
            )

class CreateCommentAPIView(APIView):
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        post_id = self.kwargs['post_id']
        serializer.save(user=self.request.user, post_id=post_id)

    def post(self, request, post_id):
        try:
            post = Post.objects.get(id=post_id)
            text = request.data.get('text')
            parent_id = request.data.get('parent_id')
            
            parent = None
            if parent_id:
                try:
                    parent = Comment.objects.get(id=parent_id)
                except Comment.DoesNotExist:
                    pass
            
            comment = Comment.objects.create(
                post=post,
                user=request.user,
                text=text,
                parent=parent
            )
            
            # Update comment count
            post.comments_count = Comment.objects.filter(post=post).count()
            post.save()
            
            serializer = CommentSerializer(comment)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Post.DoesNotExist:
            return Response(
                {"error": "Post not found"},
                status=status.HTTP_404_NOT_FOUND
            )

class LikeCommentAPIView(APIView):
    def post(self, request, comment_id):
        try:
            comment = Comment.objects.get(id=comment_id)
            user = request.user
            
            if user in comment.likes.all():
                comment.likes.remove(user)
                liked = False
            else:
                comment.likes.add(user)
                liked = True
            
            return Response({
                "liked": liked,
                "likes_count": comment.likes.count()
            })
        except Comment.DoesNotExist:
            return Response(
                {"error": "Comment not found"},
                status=status.HTTP_404_NOT_FOUND
            )

class LikePostAPIView(APIView):
    def post(self, request, post_id):
        try:
            post = Post.objects.get(id=post_id)
            user = request.user
            
            if user in post.likes.all():
                post.likes.remove(user)
                post.likes_count = post.likes.count()
                liked = False
            else:
                post.likes.add(user)
                post.likes_count = post.likes.count()
                liked = True
            
            post.save()
            return Response({
                "liked": liked,
                "likes_count": post.likes_count
            })
        except Post.DoesNotExist:
            return Response(
                {"error": "Post not found"},
                status=status.HTTP_404_NOT_FOUND
            )

#end of test nested comments and feed view

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
        hashtags_input = request.POST.get('hashtags', '')
        mentions_input = request.POST.get('mentions', '')
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
        all_hashtags = set(re.findall(r"#(\w+)", caption) + re.findall(r"#(\w+)", hashtags_input))
        for tag in all_hashtags:
            hashtag, created = Hashtag.objects.get_or_create(name=tag.lower())
            post.hashtags.add(hashtag)

        # Process mentions
        all_mentions = set(re.findall(r"@(\w+)", caption) + re.findall(r"@(\w+)", mentions_input))
        for username in all_mentions:
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
@cache_page(60 * 15)  # Cache for 15 minutes
def get_users(request):
    users = User.objects.all().values('id', 'username')
    return JsonResponse(list(users), safe=False)

@cache_page(60 * 15)
def get_hashtags(request):
    query = request.GET.get('q', '')
    # Return filtered hashtags from your database
    return JsonResponse([], safe=False)

@login_required
def hashtag_view(request, tag):
    tag = tag.lower()
    posts = Post.objects.filter(
        hashtags__name=tag
    ).select_related('user__profile').order_by('-created_at')

    return render(request, 'hashtag.html', {
        'tag': tag,
        'posts': posts,
    })


@cache_page(60 * 15)
def search_users(request):
    query = request.GET.get('q', '')
    users = User.objects.filter(username__icontains=query).values('username')
    return JsonResponse(list(users), safe=False)

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

class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    renderer_classes = [JSONRenderer, TemplateHTMLRenderer]
    pagination_class = None  # Disable pagination for notifications
    
    def get_queryset(self):
        # Filter by notification type if provided
        n_type = self.request.query_params.get('type', 'all')
        queryset = Notification.objects.filter(recipient=self.request.user).select_related('sender', 'sender__profile').order_by('-created_at')
        
        if n_type != 'all':
            # Map frontend tabs to notification types
            type_mapping = {
                'likes': ['like'],
                'comments': ['comment', 'reply'],
                'mentions': ['mention'],
                'others': ['download', 'view', 'share']
            }
            if n_type in type_mapping:
                queryset = queryset.filter(notification_type__in=type_mapping[n_type])
        
        return queryset.order_by('-created_at')
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        
        if request.accepted_renderer.format == 'html':
            return Response({
                'notifications': queryset,
                'unread_count': queryset.filter(is_read=False).count()
            }, template_name='notifications.html')
        
        return Response(serializer.data)

class MarkAllNotificationsRead(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        updated = Notification.objects.filter(
            recipient=request.user, 
            is_read=False
        ).update(is_read=True)
        
        return Response({
            'status': 'success',
            'marked_read': updated
        })

class NotificationDetailView(generics.RetrieveUpdateAPIView):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        # Mark as read when retrieved
        if not instance.is_read:
            instance.is_read = True
            instance.save()
        return super().retrieve(request, *args, **kwargs)
    
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

class ConversationRequestView(generics.CreateAPIView):
    serializer_class = ConversationRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        recipient_id = request.data.get('recipient_id')
        recipient = get_object_or_404(User, id=recipient_id)
        
        # Check if mutual follow exists
        if request.user.profile.follows.filter(user=recipient).exists() and \
           recipient.profile.follows.filter(user=request.user).exists():
            return Response({
                "detail": "You can message this user directly"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create or update request
        request_obj, created = ConversationRequest.objects.get_or_create(
            sender=request.user,
            recipient=recipient,
            defaults={'status': 'pending'}
        )
        
        if not created:
            return Response({
                "detail": "Request already exists"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Send notification to recipient
        Notification.objects.create(
            recipient=recipient,
            sender=request.user,
            notification_type='message_request',
            message=f"{request.user.username} wants to message you"
        )
        
        return Response({"status": "request_sent"}, status=status.HTTP_201_CREATED)

class ConversationRequestActionView(generics.UpdateAPIView):
    queryset = ConversationRequest.objects.all()
    serializer_class = ConversationRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        action = request.data.get('action')
        
        if instance.recipient != request.user:
            return Response({"detail": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        
        if action == 'accept':
            instance.status = 'accepted'
            instance.save()
            
            # Create conversation if it doesn't exist
            conversation, created = Conversation.objects.get_or_create()
            conversation.participants.add(instance.sender, instance.recipient)
            
            return Response({"status": "accepted"})
        
        elif action == 'reject':
            instance.status = 'rejected'
            instance.save()
            return Response({"status": "rejected"})
        
        return Response({"detail": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST)

class ConversationListView(generics.ListAPIView):
    serializer_class = ConversationRequestSerializer  # Use the correct serializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ConversationRequest.objects.filter(
            Q(sender=self.request.user) | Q(recipient=self.request.user)
        ).order_by('-created_at').prefetch_related('messages')

class ConversationRequestListView(generics.ListAPIView):
    serializer_class = ConversationRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ConversationRequest.objects.filter(
            recipient=self.request.user,
            status='pending'
        ).select_related('sender', 'sender__profile').order_by('-created_at')

class AcceptedConversationListView(generics.ListAPIView):
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Get conversations with messages
        return Conversation.objects.filter(
            participants=self.request.user
        ).annotate(
            last_message=Subquery(
                Message.objects.filter(
                    conversation=OuterRef('pk')
                ).order_by('-created_at').values('content')[:1]
            ),
            last_message_at=Max('messages__created_at'),
            unread_count=Count(
                'messages',
                filter=Q(messages__is_read=False) & 
                ~Q(messages__sender=self.request.user)
            )
        ).order_by('-last_message_at')

class ConversationRequestListView(generics.ListAPIView):
    serializer_class = ConversationRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ConversationRequest.objects.filter(
            recipient=self.request.user,
            status='pending'
        ).select_related('sender').order_by('-created_at')

class mark_all_as_read(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        # Mark all notifications as read
        updated_count = Notification.objects.filter(
            recipient=request.user, 
            is_read=False
        ).update(is_read=True)
        return Response({
            'status': 'success',
            'updated_count': updated_count
        })

#unused get_or_create_conversation function
@login_required
def get_or_create_conversation(request, user_id):
    if request.method == 'GET':
        other_user = get_object_or_404(User, id=user_id)
        conversation, created = Conversation.objects.get_or_create_between(request.user, other_user)

        return JsonResponse({
            'conversation_id': conversation.id,
            'username': other_user.username
        })

@login_required
@csrf_exempt  # Use only if CSRF is handled client-side; otherwise, ensure CSRF token is sent
def send_message(request):
    conversation_id = request.data.get('conversation')
    recipient_id = request.data.get('recipient')
    content = request.data.get('content')
    
    if conversation_id:
        conversation = get_object_or_404(
            Conversation, 
            id=conversation_id,
            participants=request.user
        )
    elif recipient_id:
        recipient = get_object_or_404(User, id=recipient_id)
        conversation, _ = Conversation.objects.get_or_create()
        conversation.participants.add(request.user, recipient)
    else:
        return Response(
            {'error': 'Either conversation or recipient must be provided'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    message = Message.objects.create(
        conversation=conversation,
        sender=request.user,
        content=content
    )
    
    # Update conversation timestamp
    conversation.save()
    
    # Create notification for recipient
    recipient = conversation.participants.exclude(id=request.user.id).first()
    if recipient:
        Notification.objects.create(
            recipient=recipient,
            sender=request.user,
            notification_type='message',
            message=f"New message from {request.user.username}",
            content_object=message
        )
    
    return Response(MessageSerializer(message).data, status=status.HTTP_201_CREATED)

class accept_message_request(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request, request_id):
        try:
            request_obj = get_object_or_404(ConversationRequest, id=request_id, recipient=request.user)
            request_obj.status = 'accepted'
            request_obj.save()
            # Create conversation if it doesn't exist
            conversation, created = ConversationRequest.objects.get_or_create(
                participants__in=[request.user, request_obj.sender]
            )
            conversation.participants.add(request.user, request_obj.sender)
            return Response({'status': 'success', 'message': 'Request accepted'})
        except ConversationRequest.DoesNotExist:
            return Response({'status': 'error', 'message': 'Request not found'}, status=404)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def accept_message_request(request, request_id):
    try:
        request_obj = get_object_or_404(
            ConversationRequest, 
            id=request_id, 
            recipient=request.user
        )
        request_obj.status = 'accepted'
        request_obj.save()
        
        # Create conversation
        conversation = Conversation.objects.create()
        conversation.participants.add(request.user, request_obj.sender)
        
        return Response({
            'status': 'success', 
            'message': 'Request accepted',
            'conversation_id': conversation.id
        })
    except ConversationRequest.DoesNotExist:
        return Response({
            'status': 'error', 
            'message': 'Request not found'
        }, status=status.HTTP_404_NOT_FOUND)


class reject_message_request(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request, request_id):
        try:
            request_obj = get_object_or_404(ConversationRequest, id=request_id, recipient=request.user)
            request_obj.status = 'rejected'
            request_obj.save()
            return Response({'status': 'success', 'message': 'Request rejected'})
        except ConversationRequest.DoesNotExist:
            return Response({'status': 'error', 'message': 'Request not found'}, status=404)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reject_message_request(request, request_id):
    try:
        request_obj = get_object_or_404(
            ConversationRequest, 
            id=request_id, 
            recipient=request.user
        )
        request_obj.status = 'rejected'
        request_obj.save()
        return Response({
            'status': 'success', 
            'message': 'Request rejected'
        })
    except ConversationRequest.DoesNotExist:
        return Response({
            'status': 'error', 
            'message': 'Request not found'
        }, status=status.HTTP_404_NOT_FOUND)

@login_required
def initiate_conversation(request, user_id):
    recipient = get_object_or_404(User, id=user_id)
    
    # Check if user is trying to message themselves
    if request.user == recipient:
        return redirect('profile', username=recipient.username)

    # Check for existing conversation request
    existing_request = ConversationRequest.objects.filter(
        (Q(sender=request.user, recipient=recipient) | 
         Q(sender=recipient, recipient=request.user))
    ).first()

    if existing_request:
        if existing_request.status == 'accepted':
            return redirect(f'/notifications/?tab=messages&open_conversation={existing_request.id}')
        return redirect('/notifications/?tab=messages')

    # Create new conversation request
    conversation_request = ConversationRequest.objects.create(
        sender=request.user,
        recipient=recipient,
        status='pending'
    )

    # Create notification
    Notification.objects.create(
        recipient=recipient,
        sender=request.user,
        notification_type='message_request',
        message=f"{request.user.username} wants to message you"
    )

    return redirect('/notifications/?tab=messages')

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_conversation(request, pk):
    conversation = get_object_or_404(ConversationRequest, id=pk)
    # Verify user is part of conversation
    if request.user not in [conversation.sender, conversation.recipient]:
        return Response(status=status.HTTP_403_FORBIDDEN)
    
    serializer = ConversationRequestSerializer(conversation)
    return Response(serializer.data)

#temporary endpoint to fetch messages in a conversation
class ConversationRequestSerializer(serializers.ModelSerializer):
    sender = serializers.SerializerMethodField()

    def get_sender(self, obj):
        return {
            'id': obj.sender.id,
            'username': obj.sender.username,
            'profile_picture': obj.sender.profile.profile_picture.url if obj.sender.profile.profile_picture else ''
        }

    class Meta:
        model = ConversationRequest
        fields = ['id', 'sender', 'status', 'created_at']

@api_view(['GET'])
def get_conversation_requests(request):
    if not request.user.is_authenticated:
        return Response({'error': 'Not authenticated'}, status=403)
    requests = ConversationRequest.objects.filter(recipient=request.user, status='pending')
    serializer = ConversationRequestSerializer(requests, many=True)
    return Response(serializer.data)

#the end of test code
@api_view(['GET'])
@login_required
def get_user_conversations(request):
    user = request.user
    conversations = ConversationRequest.objects.filter(
        Q(sender=user) | Q(recipient=user),
        status='accepted'
    ).order_by('-created_at')

    data = []
    for convo in conversations:
        other = convo.recipient if convo.sender == user else convo.sender

        messages_qs = getattr(convo, 'messages', None)
        last_msg = messages_qs.last() if messages_qs else None

        data.append({
            'id': convo.id,
            'participants': [
                {
                    'id': other.id,
                    'username': other.username,
                    'profile_picture': other.profile.profile_picture.url if hasattr(other, 'profile') else ''
                }
            ],
            'last_message': last_msg.content if last_msg else '',
            'last_message_at': last_msg.created_at if last_msg else convo.created_at,
            'unread_count': messages_qs.filter(is_read=False).exclude(sender=user).count() if messages_qs else 0
        })

    return Response(data)

@api_view(['GET'])
def get_conversation_messages(request, conversation_id):
    user = request.user
    conversation = get_object_or_404(ConversationRequest, id=conversation_id, status='accepted')

    # Only allow sender or recipient to view
    if user != conversation.sender and user != conversation.recipient:
        return Response({'error': 'Unauthorized'}, status=403)

    messages = Message.objects.filter(conversation=conversation).order_by('created_at')

    data = [
        {
            'id': msg.id,
            'sender': {
                'id': msg.sender.id,
                'username': msg.sender.username
            },
            'content': msg.content,
            'created_at': msg.created_at.isoformat(),
            'is_read': msg.is_read
        } for msg in messages
    ]

    return Response(data)

@api_view(['POST'])
def send_message(request):
    user = request.user
    recipient_id = request.data.get('recipient')
    content = request.data.get('content')

    if not recipient_id or not content:
        return Response({'error': 'Recipient and content are required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        recipient = User.objects.get(id=recipient_id)
    except User.DoesNotExist:
        return Response({'error': 'Recipient not found'}, status=status.HTTP_404_NOT_FOUND)

    # Get or create accepted conversation
    convo = ConversationRequest.objects.filter(
        ((Q(sender=user) & Q(recipient=recipient)) |
         (Q(sender=recipient) & Q(recipient=user))),
        status='accepted'
    ).first()

    if not convo:
        return Response({'error': 'No accepted conversation found'}, status=status.HTTP_403_FORBIDDEN)

    message = Message.objects.create(
        conversation=convo,
        sender=user,
        content=content
    )

    return Response({
        'id': message.id,
        'sender': {
            'id': user.id,
            'username': user.username
        },
        'content': message.content,
        'created_at': message.created_at.isoformat(),
        'is_read': message.is_read
    }, status=status.HTTP_201_CREATED)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def conversation_messages(request):
    conversation_id = request.GET.get('conversation')
    if not conversation_id:
        return Response({'error': 'conversation parameter required'}, status=400)
    
    conversation = get_object_or_404(ConversationRequest, id=conversation_id)
    # Verify user is part of conversation
    if request.user not in [conversation.sender, conversation.recipient]:
        return Response(status=status.HTTP_403_FORBIDDEN)
    
    messages = Message.objects.filter(conversation=conversation).order_by('created_at')
    serializer = MessageSerializer(messages, many=True)
    return Response(serializer.data)

class ConversationMessagesView(generics.ListAPIView):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        conversation_id = self.kwargs['conversation_id']
        conversation = get_object_or_404(
            Conversation, 
            id=conversation_id,
            participants=self.request.user
        )
        
        # Mark messages as read when fetched
        Message.objects.filter(
            conversation=conversation,
            is_read=False
        ).exclude(sender=self.request.user).update(is_read=True)
        
        return Message.objects.filter(
            conversation=conversation
        ).order_by('created_at')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_message(request):
    conversation_id = request.data.get('conversation')
    content = request.data.get('content')
    
    if not conversation_id or not content:
        return Response({'error': 'conversation and content are required'}, status=400)
    
    conversation = get_object_or_404(ConversationRequest, id=conversation_id)
    
    # Verify user is part of conversation
    if request.user not in [conversation.sender, conversation.recipient]:
        return Response(status=status.HTTP_403_FORBIDDEN)
    
    message = Message.objects.create(
        conversation=conversation,
        sender=request.user,
        content=content
    )
    
    # Create notification for recipient
    recipient = conversation.sender if conversation.recipient == request.user else conversation.recipient
    Notification.objects.create(
        recipient=recipient,
        sender=request.user,
        notification_type='message',
        message=f"New message from {request.user.username}",
        content_object=message
    )
    
    return Response(MessageSerializer(message).data, status=status.HTTP_201_CREATED)

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

    def serialize_user(user):
        profile = getattr(user, 'profile', None)
        return {
            "username": user.username,
            "profile_picture": profile.profile_picture.url if profile and profile.profile_picture else None
        }

    if request.method == 'GET':
        all_comments = Comment.objects.filter(post=post).select_related('user', 'parent').order_by('created_at')

        data = []
        for comment in all_comments:
            data.append({
                "id": comment.id,
                "text": comment.text,
                "created_at": comment.created_at,
                "user": serialize_user(comment.user),
                "parent": comment.parent.id if comment.parent else None,
                "likes_count": comment.likes.count(),
                "is_liked": request.user.is_authenticated and comment.likes.filter(id=request.user.id).exists()
            })

        return Response(data)

    elif request.method == 'POST':
        text = request.data.get('text')
        parent_id = request.data.get('parent')

        if not text or text.strip() == '':
            return Response({"error": "Comment text is required"}, status=status.HTTP_400_BAD_REQUEST)

        parent = get_object_or_404(Comment, id=parent_id) if parent_id else None

        comment = Comment.objects.create(
            text=text.strip(),
            user=request.user,
            post=post,
            parent=parent
        )

        UserInteraction.objects.create(
            user=request.user,
            post=post,
            interaction_type='comment'
        )

        post.comments_count = Comment.objects.filter(post=post).count()
        post.save()

        return Response({
            "id": comment.id,
            "text": comment.text,
            "created_at": comment.created_at,
            "user": serialize_user(comment.user),
            "parent": comment.parent.id if comment.parent else None
        }, status=status.HTTP_201_CREATED)


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