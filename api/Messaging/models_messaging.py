from django.db import models
from api.Account.models_account import Account
from api.Contact.models_contact import Contact


class Tag(models.Model):
    tag_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50)
    account_id = models.ForeignKey(Account, on_delete=models.CASCADE)

    # class Meta:
    #     permissions = [
    #         ('can_create_tag', 'Can create tag'),
    #         ('can_edit_tag', 'Can edit tag'),
    #         ('can_delete_tag', 'Can delete tag'),
    #         ('can_view_tag', 'Can view tag'),
    #     ]

    def __str__(self) -> str:
        return self.name


class Group(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    contact = models.ManyToManyField(Contact)

    # class Meta:
    #     permissions = [
    #         ('can_create_group', 'Can create group'),
    #         ('can_edit_group', 'Can edit group'),
    #         ('can_delete_group', 'Can delete group'),
    #         ('can_view_group', 'Can view group'),
    #     ]

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

    # class Meta:
    #     permissions = [
    #         ('can_create_quick_reply', 'Can create quick reply'),
    #         ('can_edit_quick_reply', 'Can edit quick reply'),
    #         ('can_delete_quick_reply', 'Can delete quick reply'),
    #         ('can_view_quick_reply', 'Can view quick reply'),
    #     ]

    def __str__(self) -> str:
        return self.name
