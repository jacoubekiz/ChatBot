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

    def __str__(self) -> str:
        return self.name
