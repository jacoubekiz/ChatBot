from django.db import models
from api.Account.models_account import Account


METHOD_CHOICES = (
    ('GET', 'GET'),
    ('POST', 'POST'),
    ('PUT', 'PUT'),
    ('DELETE', 'DELETE'),
)

TYPE_PARAM = (
    ('parameter', 'parameter'),
    ('header', 'header')
)


class Parameter(models.Model):
    parameter_id = models.AutoField(primary_key=True)
    account_id = models.ForeignKey(Account, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return f'parameter for account {self.account_id.name}'
     

class API(models.Model):
    api_id = models.AutoField(primary_key=True)
    account_id = models.ForeignKey(Account, on_delete=models.CASCADE)
    parameters = models.ManyToManyField(Parameter, through="api_parameter")
    api_name = models.CharField(max_length=50, null=True, blank=True)
    endpoint = models.URLField(max_length=200, null=True, blank=True)
    method = models.CharField(max_length=10, choices=METHOD_CHOICES, null=True, blank=True)
    body = models.JSONField(null=True, blank=True)
    response = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f'api {self.api_name} for account {self.account_id.name}'


class Api_parameter(models.Model):
    api = models.ForeignKey(API, on_delete=models.CASCADE)
    parameter = models.ForeignKey(Parameter, on_delete=models.CASCADE)
    type = models.CharField(choices=TYPE_PARAM, max_length=50, null=True, blank=True)
    key = models.CharField(max_length=100, null=True, blank=True)
    value = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self) -> str:
        return f'parameter {self.key} for api {self.api.api_name}'


class APILog(models.Model):
    apilog_id = models.AutoField(primary_key=True)
    api = models.ForeignKey(API, on_delete=models.CASCADE)
    response = models.JSONField(blank=True, null=True)
    status_request = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f'api log for api {self.api.api_name}'
