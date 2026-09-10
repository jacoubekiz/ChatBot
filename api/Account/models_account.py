from django.db import models
import secrets
from api.Auth.models_auth import CustomUser


class Account(models.Model):
    account_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, default=1)
    apiKey = models.CharField(max_length=255, unique=True, null=True, blank=True)
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    # class Meta:
    #     permissions = [
    #         ('can_create_account', 'Can create account'),
    #         ('can_edit_account', 'Can edit account'),
    #         ('can_delete_account', 'Can delete account'),
    #         ('can_view_account', 'Can view account'),
    #     ]

    def __str__(self) -> str:
        return self.name

    @staticmethod
    def generate_key():
        return secrets.token_urlsafe(128)


class Team(models.Model):
    team_id = models.AutoField(primary_key=True)
    account_id = models.ForeignKey(Account, on_delete=models.CASCADE)
    members = models.ManyToManyField(CustomUser)
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        permissions = [
    #         ('can_create_team', 'Can create team'),
    #         ('can_edit_team', 'Can edit team'),
    #         ('can_delete_team', 'Can delete team'),
    #         ('can_view_team', 'Can view team'),
            ('can_manage_team_members', 'Can manage team members'),
        ]

    def __str__(self) -> str:
        return self.name
