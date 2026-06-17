from django.db import models
from django.conf import settings
from api.Account.models_account import Account, Team
from api.Auth.models_auth import CustomUser


TYPE_SETTTING = (
    ('business_hours', 'business_hours'),
    ('integrations', 'integrations'),
    ('labels', 'labels'),
    ('quick_replies', 'quick_replies')
)


class TestWebhook(models.Model):
    test_text = models.CharField(max_length=50)
    name = models.CharField(max_length=20)

    def __str__(self) -> str:
        return self.test_text


class InternalChat(models.Model):
    caht_id = models.AutoField(primary_key=True)
    team_id = models.ForeignKey(Team, on_delete=models.CASCADE)
    user_id = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    content = models.TextField(null=True, blank=True)
    sent_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f'internal caht for team {self.team_id.name}'


class Report(models.Model):
    report_id = models.AutoField(primary_key=True)
    account_id = models.ForeignKey(Account, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=50, null=True, blank=True)
    data = models.FileField(upload_to='Reposts', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f'report for account {self.account_id.name}'


class ChatbotBuilder(models.Model):
    bot_id = models.AutoField(primary_key=True)
    account_id = models.ForeignKey(Account, on_delete=models.CASCADE)
    name = models.CharField(max_length=50, null=True, blank=True)
    configuration = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f' chat bot builder {self.name} for account {self.account_id.name}'


class Setting(models.Model):
    setting_id = models.AutoField(primary_key=True)
    account_id = models.ForeignKey(Account, on_delete=models.CASCADE)
    type_setting = models.CharField(choices=TYPE_SETTTING, max_length=50, null=True, blank=True)
    config_data = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f'setting for account {self.account_id.name}'


class UploadImage(models.Model):
    image_file = models.FileField(upload_to='chat_message/')

    @property
    def get_absolute_url(self):
        return f"{settings.MEDIA_URL}{self.image_file.name}"
