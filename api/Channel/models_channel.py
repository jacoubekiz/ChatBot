from django.db import models
from api.Account.models_account import Account
from api.Flow.models_flow import Flow


TYPE_CHANNLE = (
    ('WhatsApp', 'WhatsApp'),
)


class Channle(models.Model):
    channle_id = models.AutoField(primary_key=True)
    account_id = models.ForeignKey(Account, on_delete=models.CASCADE)
    type_channle = models.CharField(choices=TYPE_CHANNLE, max_length=25)
    tocken = models.TextField(max_length=600)
    phone_number = models.PositiveBigIntegerField()
    phone_number_id = models.PositiveBigIntegerField()
    organization_id = models.PositiveBigIntegerField(default=1)
    name = models.CharField(max_length=50)
    flows = models.ManyToManyField(Flow, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name
