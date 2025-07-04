from django.urls import path, include
from . import views
from django.contrib.auth.views import LoginView
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from .views import NotificationListView, NotificationDetailView, MarkNotificationAsRead, MarkAllNotificationsRead, ConversationListView, PostViewSet, FeedViewSet, ProfileViewSet, CommentViewSet, api_follow_user, ConversationRequestView, ConversationRequestActionView, accept_message_request, reject_message_request, MarkAllNotificationsRead, ConversationRequestListView, AcceptedConversationListView, send_message, get_conversation_requests, custom_logout, delete_post
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView



router = DefaultRouter()
router.register(r'posts', PostViewSet, basename='post')
router.register(r'feed', FeedViewSet, basename='feed')
router.register(r'profiles', ProfileViewSet, basename='profile')
router.register(r'comments', CommentViewSet, basename='comment')


urlpatterns = [
    path('', views.welcome),
    path('signin/', views.signin, name='signin'),
    path('terms/', views.terms_and_conditions, name='terms'),
    path('login/', LoginView.as_view(template_name='log-in.html'), name='login'),
    path('forgot_password/', views.forgot_password, name = 'forgot_password'),
    path('feed/', views.feed, name='feed'),
    path('api/', include(router.urls)),
    path('api/search/', views.search_view, name='search'),
    path('api/posts/<int:post_id>/download/', views.download_media, name='download-media'),
    path('live/', views.live, name='live'),
    path('api/create_stream/', views.create_stream, name='create_stream'),
    path('api/end_stream/', views.end_stream, name='end_stream'),
    #path('watch/<int:stream_id>/', views.watch_live, name='watch_live'),
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
    path('api/upload/', views.upload_media, name='upload_media'),
    path('api/posts/<int:post_id>/like', views.like_post, name='like_post'),
    path('api/posts/<int:post_id>/comments/', views.post_comments, name='post-comments'),
    path('api/users/', views.get_users, name='get_users'),
    path('api/hashtags/', views.get_hashtags),
    path('api/users/search/', views.search_users),
    path('friends/', views.friends, name='friends'),
    path('api/comprehensive_search/', views.comprehensive_search, name='comprehensive_search'),
    path('notifications/', NotificationListView.as_view(), name='notification-list'),
    path('notifications/mark_all_read/', MarkAllNotificationsRead.as_view(), name='mark-all-notifications-read'),
    path('notifications/<int:pk>/', NotificationDetailView.as_view(), name='notification-detail'),
    path('api/notifications/mark_all_as_read/', MarkAllNotificationsRead.as_view(), name='mark-all-notifications-read'),
    path('api/users/<int:pk>/follow/', views.follow_user),
    path('notifications/stream/', NotificationListView.as_view(), name='notification-stream'),
    path('conversations/request/', ConversationRequestView.as_view(), name='conversation-request'),
    path('conversations/request/<int:pk>/action/', ConversationRequestActionView.as_view(), name='conversation-request-action'),
    path('conversations/', ConversationListView.as_view(), name='conversation-list'),
    path('api/conversations/', views.get_user_conversations, name='api-conversations'),
    path('initiate-conversation/<int:user_id>/', views.initiate_conversation, name='initiate-conversation'),
    path('api/accepted-conversations/', AcceptedConversationListView.as_view(), name='accepted-conversations'),
    path('api/follow/<int:user_id>/', views.api_follow_user, name='api-follow-user'),
    path('api/conversations/<int:pk>/', views.get_conversation, name='get-conversation'),
    path('api/auth/', include('rest_framework.urls')),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('send-message/', views.send_message, name='send_message'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/send-message/', send_message, name='send-message'),
    path('api/messages/requests/', views.get_conversation_requests, name='conversation-request-list'),
    path('api/messages/requests/<int:request_id>/accept/', accept_message_request, name='accept-message-request'),
    path('api/messages/<int:conversation_id>/', views.get_conversation_messages),
    path('api/messages/requests/<int:request_id>/reject/', reject_message_request, name='reject-message-request'),
    path('api/messages/send/', views.send_message),
    path('api/messages/<int:user_id>/', views.get_or_create_conversation, name='get_or_create_conversation'),
    path('api/delete-post/<int:post_id>/', views.delete_post, name='delete_post'),
    path('logout/', views.custom_logout, name='logout'),
    path('account/settings/', views.account_settings, name='account_settings'),
    path('privacy/settings/', views.privacy_settings, name='privacy_settings'),
    path('help/center/', views.help_center, name='help_center'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
