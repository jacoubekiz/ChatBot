from django.db import models
from api.Account.models_account import Account
from api.Channel.models_channel import Channle
from api.Flow.models_flow import Flow

class Template(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    template_id = models.CharField(max_length= 100)
    template_name = models.CharField(max_length= 100)

    def __str__(self):
        return f"{self.template_name} for account {self.account.name}"

class TemplateBox(models.Model):
    account = models.OneToOneField(Account, on_delete=models.CASCADE)
    box_name = models.CharField(max_length= 100)
    template_buttons = models.ManyToManyField(Template, through="TemplateBoxTemplate")
    
    def __str__(self):
        return f"{self.box_name} for account {self.account.name}"

class TemplateBoxTemplate(models.Model):
    template_box = models.ForeignKey(TemplateBox, on_delete=models.CASCADE)
    template = models.ForeignKey(Template, on_delete=models.CASCADE)
    button_name = models.CharField(max_length= 100)
    flow = models.ForeignKey(Flow, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"{self.template_box.box_name} - {self.template.template_name}"

