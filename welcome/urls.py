from django.urls import path, include
from . import views
from django.contrib.auth.views import LoginView, LogoutView
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from .views import NotificationListView, MarkNotificationAsRead, ConversationListView, ConversationCreateView, MessageListView, UnreadCountView, PostViewSet, FeedViewSet, ProfileViewSet, CommentViewSet, api_follow_user
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView



router = DefaultRouter()
router.register(r'posts', PostViewSet, basename='post')
router.register(r'feed', FeedViewSet, basename='feed')
router.register(r'profiles', ProfileViewSet, basename='profile')
router.register(r'comments', CommentViewSet, basename='comment')



urlpatterns = [
    path('', views.welcome),
    path('signin/', views.signin, name='signin'),
    path('login/', LoginView.as_view(template_name='log-in.html'), name='login'),
    path('forgot_password/', views.forgot_password, name = 'forgot_password'),
    path('feed/', views.feed, name='feed'),
    path('api/', include(router.urls)),
    path('live/', views.live, name='live'),
    path('api/create_stream/', views.create_stream, name='create_stream'),
    path('api/end_stream/', views.end_stream, name='end_stream'),
    #path('watch/<int:stream_id>/', views.watch_live, name='watch_live'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('profile/', views.my_profile, name='my-profile'),
    path('profile/<str:username>/', views.profile_view, name='profile'),
    path('users/<int:pk>/', ProfileViewSet.as_view(
        {'get': 'retrieve', 'put': 'update', 'patch': 'partial_update'}
    ), name='user-detail'),
    path('profile/<str:username>/', views.profile_view, name='profile'),
    path('profile/change-picture/', views.change_profile_picture, name='change_profile_picture'),
    path('follow/<int:user_id>/', views.follow_user, name='follow_user'),
    path('profile/<str:username>/follow/', views.follow_user, name='follow_user'),
    path('profile/<str:username>/followers/', views.followers_list, name='followers'),
    path('profile/<str:username>/following/', views.following_list, name='following'),
    path('api/follow/<int:user_id>/', api_follow_user, name='api-follow'),
    path('edit-profile/', views.edit_profile, name='edit-profile'),
    path('post/<int:post_id>/save/', views.save_post, name='save-post'),
    path('upload/', views.upload_page, name="upload_page"),
    #path('api/posts/create/', PostViewSet.as_view({'post': 'create'}), name='post-create')
    path('api/upload/', views.upload_media, name='upload_media'),
    path('api/posts/<int:post_id>/like', views.like_post, name='like_post'),
    path('api/posts/<int:post_id>/comments/', views.post_comments, name='post-comments'),
    path('api/users/', views.get_users, name='get_users'),
    path('api/hashtags/', views.get_hashtags),
    path('api/users/search/', views.search_users),
    path('friends/', views.friends, name='friends'),
    path('notifications/', NotificationListView.as_view(), name='notification-list'),
    path('notifications/<int:pk>/read/', MarkNotificationAsRead.as_view(), name='mark-notification-read'),
    path('conversations/', ConversationListView.as_view(), name='conversation-list'),
    path('conversations/create/', ConversationCreateView.as_view(), name='conversation-create'),
    path('conversations/<int:conversation_id>/messages/', MessageListView.as_view(), name='message-list'),
    path('unread-count/', UnreadCountView.as_view(), name='unread-count'),
    path('api/auth/', include('rest_framework.urls')),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    #path('api/messaging/', include('messaging.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
