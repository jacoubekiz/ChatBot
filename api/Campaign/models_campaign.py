from django.db import models
from api.Account.models_account import Account
from api.Contact.models_contact import Contact
from api.Auth.models_auth import CustomUser


STATUS_CAMPAIGN = (
    ('draft', 'Draft'),
    ('scheduled', 'Scheduled'),
    ('ongoing', 'ongoing'),
    ('completed', 'Completed'),
    ('failed', 'Failed'),
)

STATUS_MESSAGE = (
    ('sent', 'sent'),
    ('delivered', 'delivered'),
    ('read', 'read'),
    ('failed', 'failed'),
    ('pending', 'pending')
)


class WhatsAppCampaign(models.Model):
    campaign_id = models.AutoField(primary_key=True)
    account_id = models.ForeignKey(Account, on_delete=models.CASCADE, blank=True, null=True)
    name = models.CharField(max_length=50, null=True, blank=True)
    status = models.CharField(choices=STATUS_CAMPAIGN, max_length=20, default='ongoing')
    csv_file = models.FileField(upload_to='campaigns/csv/')
    template_name = models.CharField(max_length=100)
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    total_recipients = models.IntegerField(default=0)
    sent_count = models.IntegerField(default=0, blank=True, null=True)
    failed_count = models.IntegerField(default=0, blank=True, null=True)
    scheduled_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        
    def __str__(self) -> str:
        return f'campaign for account {self.account_id.name}'


class AnalyticsCampaign(models.Model):
    analytics_id = models.AutoField(primary_key=True)
    account_id = models.ForeignKey(Account, on_delete=models.CASCADE)
    campaign_id = models.ForeignKey(WhatsAppCampaign, on_delete=models.CASCADE)
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE)
    status_message = models.CharField(choices=STATUS_MESSAGE, max_length=20)
    error_message = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f'Analytics for campaign {self.campaign_id.name}'
