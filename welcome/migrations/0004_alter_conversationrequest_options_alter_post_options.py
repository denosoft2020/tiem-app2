# Generated by Django 5.1.6 on 2025-06-20 15:11

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('welcome', '0003_conversationrequest_alter_message_conversation_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='conversationrequest',
            options={'ordering': ['-created_at']},
        ),
        migrations.AlterModelOptions(
            name='post',
            options={'ordering': ['-created_at']},
        ),
    ]
