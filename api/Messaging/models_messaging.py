from django.db import models
from api.Account.models_account import Account
from api.Contact.models_contact import Contact


class Tag(models.Model):
    tag_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50)
    account_id = models.ForeignKey(Account, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return self.name


class Group(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    contact = models.ManyToManyField(Contact)

    def __str__(self) -> str:
        return self.name


class QuickReply(models.Model):
    quickreply_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    payload = models.CharField(max_length=255, null=True, blank=True)
    image = models.ImageField(upload_to='quick_replies/', null=True, blank=True)
    account_id = models.ForeignKey(Account, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name
