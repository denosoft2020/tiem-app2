from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from .models import Profile, Notification, Message, Post, Like, Comment, User, UserInteraction, FollowRelationship
from django.contrib.contenttypes.models import ContentType

@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        if not hasattr(instance, 'profile'):
            Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_profile(sender, instance, **kwargs):
    instance.profile.save()

#for notifications

@receiver(post_save, sender=Like)
def create_like_notification(sender, instance, created, **kwargs):
    if created and instance.post.user != instance.user:
        Notification.objects.create(
            recipient=instance.post.user,
            sender=instance.user,
            notification_type='like',
            content_object=instance.post
        )

@receiver(post_save, sender=Comment)
def create_comment_notification(sender, instance, created, **kwargs):
    if created and instance.post.user != instance.user:
        Notification.objects.create(
            recipient=instance.post.user,
            sender=instance.user,
            notification_type='comment',
            content_object=instance.post
        )

@receiver(post_save, sender=FollowRelationship)
def create_follow_notification(sender, instance, created, **kwargs):
    if created:
        Notification.objects.create(
            recipient=instance.following.user,
            sender=instance.follower.user,
            notification_type='follow'
        )

@receiver(post_save, sender=UserInteraction)
def create_interaction_notification(sender, instance, created, **kwargs):
    if created:
        if instance.interaction_type == 'download' and instance.post.user != instance.user:
            Notification.objects.create(
                recipient=instance.post.user,
                sender=instance.user,
                notification_type='download',
                content_object=instance.post
            )
        elif instance.interaction_type == 'share' and instance.post.user != instance.user:
            Notification.objects.create(
                recipient=instance.post.user,
                sender=instance.user,
                notification_type='share',
                content_object=instance.post
            )