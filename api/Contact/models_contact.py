from django.db import models
from api.Account.models_account import Account
from api.Auth.models_auth import CustomUser


STATUS = (
    ('open', 'open'),
    ('closed', 'closed'),
    ('in_progress', 'in_progress'),
    ('review', 'review'),
    ('pending', 'pending'),
    ('onhold', 'onhold'),
    ('dependency', 'dependency'),
    ('lock', 'lock'),
)

STATUS_CONVERSATION = (
    ('end_bot', 'end_bot'),
    ('start_bot', 'start_bot'),
    ("live_chat", "live_chat")
)

CONTENT_TYPE = (
    ('text', 'text'),
    ('image', 'imgage'),
    ('video', 'video'),
    ('document', 'document'),
    ('audio', 'audio'),
    ('template', 'template')
)

STATUS_MESSAGE = (
    ('sent', 'sent'),
    ('delivered', 'delivered'),
    ('read', 'read'),
    ('failed', 'failed'),
    ('pending', 'pending')
)

STATUS_MESSAGE_STATUS = (
    ('sent', 'sent'),
    ('delivered', 'delivered'),
    ('read', 'read')
)


class Contact(models.Model):
    contact_id = models.AutoField(primary_key=True)
    account_id = models.ForeignKey(Account, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=50, null=True, blank=True)
    phone_number = models.BigIntegerField()
    email = models.EmailField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        if self.name:
            return self.name
        else:
            return str(self.phone_number)


class Conversation(models.Model):
    conversation_id = models.AutoField(primary_key=True)
    account_id = models.ForeignKey(Account, on_delete=models.CASCADE, null=True, blank=True)
    channle_id = models.ForeignKey('api.Channle', on_delete=models.CASCADE, null=True, blank=True)
    contact_id = models.ForeignKey(Contact, on_delete=models.CASCADE, null=True, blank=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    status = models.CharField(choices=STATUS, max_length=20, default='open')
    state = models.CharField(choices=STATUS_CONVERSATION, max_length=100, blank=True, null=True, default='start_bot')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    tags = models.ManyToManyField('api.Tag', blank=True)

    def __str__(self) -> str:
        return f'conversation for contact {self.contact_id.name}'


class ChatMessage(models.Model):
    message_id = models.AutoField(primary_key=True)
    from_message = models.CharField(max_length=30, default='bot')
    conversation_id = models.ForeignKey(Conversation, on_delete=models.CASCADE)
    user_id = models.ForeignKey(CustomUser, on_delete=models.CASCADE, blank=True, null=True)
    content_type = models.CharField(choices=CONTENT_TYPE, max_length=20)
    content = models.TextField(max_length=1000, blank=True, null=True)
    caption = models.CharField(max_length=500, blank=True, null=True)
    wamid = models.CharField(max_length=500)
    error_message = models.CharField(max_length=1000, null=True, blank=True)
    status_message = models.CharField(choices=STATUS_MESSAGE, max_length=20, default='sent')
    status_updated_at = models.DateTimeField(auto_now_add=True)
    media_url = models.URLField(null=True, blank=True)
    media_mime_type = models.CharField(max_length=500, null=True, blank=True)
    media_sha256_hash = models.CharField(max_length=256, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f'message {self.message_id}'


class MessageStatus(models.Model):
    status_id = models.AutoField(primary_key=True)
    message_id = models.ForeignKey(ChatMessage, on_delete=models.CASCADE)
    status = models.CharField(choices=STATUS_MESSAGE_STATUS, max_length=25)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f'message id {self.message_id.message_id} status is {self.status}'


class MediaManagement(models.Model):
    media_id = models.AutoField(primary_key=True)
    message_id = models.ForeignKey(ChatMessage, on_delete=models.CASCADE)
    media_url = models.URLField(null=True, blank=True)
    file_type = models.CharField(choices=CONTENT_TYPE, max_length=25, null=True, blank=True)
    mime_type = models.CharField(max_length=50, null=True, blank=True)
    size = models.BigIntegerField(null=True, blank=True)
    hash256_sha = models.CharField(max_length=256, null=True, blank=True)
    uploded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f'media management for message id {self.message_id.message_id}'
