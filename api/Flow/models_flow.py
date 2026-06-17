from django.db import models
from django.utils import timezone
from api.Account.models_account import Account


SAVE_API = (
    ('False', 'False'),
    ('True', 'True')
)


class Flow(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE, null=True, blank=True)
    flow_name = models.CharField(max_length=100)
    flow = models.FileField(upload_to='flows/')
    is_default = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f'{self.flow}'


class Trigger(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE, null=True, blank=True)
    flow = models.ForeignKey(Flow, on_delete=models.CASCADE, null=True, blank=True)
    trigger = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self) -> str:
        return self.trigger


class Chat(models.Model):
    channel_id = models.ForeignKey('api.Channle', null=True, blank=True, on_delete=models.CASCADE, default='1')
    flow = models.ForeignKey(Flow, on_delete=models.CASCADE, null=True, blank=True)
    state = models.CharField(max_length=255, blank=True, null=True, default='start')
    conversation_id = models.CharField(max_length=255, blank=True, null=True)
    isSent = models.BooleanField(default=False, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    last_state_change = models.DateTimeField(default=timezone.now)
    
    
    def update_state(self, new_state):
        self.state = new_state
        self.last_state_change = timezone.now()
        self.save()
        
    def __str__(self) -> str:
        return f"{self.conversation_id} Client -> {self.channel_id}, State -> {self.state}"


class Attribute(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    key = models.CharField(max_length=255)
    chat = models.ManyToManyField(Chat, through='custome_attribute')
    save_api = models.CharField(choices=SAVE_API, default='False')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f'{self.key} for save reply user' if self.save_api == 'False' else f'{self.key} for save response form api'


class Custome_attribute(models.Model):
    attribute = models.ForeignKey(Attribute, on_delete=models.CASCADE)
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, blank=True, null=True)
    value = models.CharField(max_length=255, blank=True, null=True, default='Unknown')
    variable = models.CharField(max_length=50, blank=True, null=True)
    api = models.ForeignKey('api.API', on_delete=models.CASCADE, blank=True, null=True)


class RestartKeyword(models.Model):
    keyword = models.CharField(max_length=255)
    channel_id = models.ForeignKey('api.Channle', on_delete=models.CASCADE, related_name='restart_keyword', default='1')
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
