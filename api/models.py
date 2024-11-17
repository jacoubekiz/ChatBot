from django.db import models
import hashlib
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import AbstractUser
from .configure_api import *
import secrets

Days = (
    ('1','الأحد'),
    ('2', 'الإثنين'),
    ('3', 'الثلاثاء'),
    ('4', 'الأربعاء'),
    ('5', 'الخميس'),
    ('6', 'الجمعة'),
    ('7', 'السبت'),
)
class CustomUser(AbstractUser):
    email = models.EmailField(max_length=40, unique=True)
    # phonenumber = models.BigIntegerField(default=352353525)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username',]

    def __str__(self) -> str:
        return self.username

class Duration(models.Model):
    duration = models.DurationField()

    def __str__(self) -> str:
        return str(self.duration)


class WorkingTime(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    day = models.CharField(max_length=20, choices=Days)
    starting_time_am = models.TimeField(null=True, blank=True)
    end_time_am = models.TimeField(null=True, blank=True)
    starting_time_pm = models.TimeField(null=True, blank=True)
    end_time_pm = models.TimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f'working time for {self.user.username}'

class Calendar(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    working_time = models.ManyToManyField(WorkingTime)
    key = models.CharField(max_length=255, unique=True)
    duration = models.ForeignKey(Duration, on_delete=models.CASCADE)
    start_appointment = models.DateField(default='2024-11-10')
    end_appointment = models.DateField(default='2024-11-10')

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        return super().save(*args, **kwargs)
    
    @staticmethod
    def generate_key():
        return secrets.token_urlsafe(32)
    
    def __str__(self) -> str:
        return f"calendar for {self.user.username}"

class BookAnAppointment(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    details = models.CharField(max_length=300, null=True, blank=True)
    patientName = models.CharField(max_length=50)
    day =  models.DateField()
    hour = models.TimeField()
    duration = models.DurationField()
    is_proccessed = models.BooleanField(default=False, blank=True, null=True)
    created = models.DateField(auto_now_add=True)

    def __str__(self) -> str:
        return f"book an appointment for {self.user.username} from {convert_time_to_timedelta(self.hour)} to {convert_time_to_timedelta(self.hour) + self.duration}"
    
    class Meta:
        ordering = ['day', 'hour']

# add new futures ------------------------------------------------
class Trigger(models.Model):
    trigger = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self) -> str:
        return self.trigger
        
class Flow(models.Model):
    flow = models.FileField(upload_to='flows/')
    trigger = models.ManyToManyField(Trigger, null=True, blank=True)
    is_default = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f'{self.flow}-{self.trigger}'
# ------------------------------------------------------------------
class Client(models.Model):
    name = models.CharField(max_length=255, null=True)
    flow = models.ManyToManyField(Flow)
    resetting_minutes = models.PositiveIntegerField(null=True, default = 60)
    wa_id = models.CharField(max_length=700, null=True)
    token = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    
    @property
    def client_endpoint(self):
        client_id_hash = hashlib.sha256(str(self.id).encode()).hexdigest()
        
        if settings.DEBUG:
            return f'http://localhost:8000/api/?client={client_id_hash}'
        else:
            return f'https://chatbot.icsl.me/api/?client={client_id_hash}'
        
    def __str__(self):
        return self.name

 
class RestartKeyword(models.Model):
    keyword = models.CharField(max_length=255)
    client =  models.ForeignKey(Client, on_delete=models.CASCADE, related_name='restart_keyword')
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    
class Chat(models.Model):
    client = models.ForeignKey(Client, null=True, blank=True, on_delete=models.CASCADE)
    flow = models.ForeignKey(Flow, on_delete=models.CASCADE)
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
        return f"{self.conversation_id} Client -> {self.client}, State -> {self.state}"
    
class Attribute(models.Model):
    key = models.CharField(max_length=255)
    value = models.CharField(max_length=255, blank=True, null=True, default='Unknown')
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f'{self.key} - {self.value}'
    


class NextTenDay(models.Model):
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE)
    day = models.DateField()
    day_end = models.DateField(default='2024-05-5')


class NextTime(models.Model):
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE)
    time = models.TimeField()
    # end_time = models.TimeField()
    

class MessageChat(models.Model):
    message = models.CharField(max_length=100)

    def __str__(self) -> str:
        return self.message
    
# class Testing(models.Model):
#     test = models.CharField(max_length=30)

# class BusyTime(models.Model):
#     user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
#     day = models.CharField(max_length=25)
#     starting_time = models.TimeField()
#     duration = models.DurationField()
#     created = models.DateField(auto_now_add=True)
#     is_proccessed = models.BooleanField(default=False)


# class WorkingHoursAM(models.Model):
#     day = models.CharField(max_length=25, choices=Days)
#     starting_time = models.TimeField()
#     expire_time = models.TimeField()

    # def __str__(self) -> str:
    #     return f"from {str(self.starting_time)} to {str(self.expire_time)}"
    
# class WorkingHoursPM(models.Model):
#     day = models.CharField(max_length=25, choices=Days)
#     starting_time = models.TimeField()
#     expire_time = models.TimeField()

    # def __str__(self) -> str:
    #     return f"from {str(self.starting_time)} to {str(self.expire_time)}"
















class TestWebhook(models.Model):
    test_text = models.CharField(max_length=50)
    name = models.CharField(max_length=20)

    def __str__(self) -> str:
        return self.test_text


# models.py


ROLE = (
    ('admin', 'admin'),
    ('agent', 'agent')
)

TYPE_CHANNLE = (
    ('WhatsApp', 'WhatsApp'),
)

STATUS = (
    ('open', 'open'),
    ('closed', 'closed'),
    ('pending', 'pending')
)

CONTENT_TYPE = (
    ('text', 'text'),
    ('image', 'imgage'),
    ('video', 'video'),
    ('document', 'document'),
    ('audio', 'audio')
)

STATUS_MESSAGE = (
    ('sent', 'sent'),
    ('delivered', 'delivered'),
    ('read', 'read'),
    ('failed', 'failed'),
    ('pending', 'pending')
)

STATUS_MESSAGE_STATUS = (
    ('sent', 'sent'),
    ('delivered', 'delivered'),
    ('read', 'read')
)

STATUS_CAMPAIGN = (
    ('active', 'active'),
    ('inactive', 'inactive'),
    ('complated', 'complated')
)

TYPE_SETTTING = (
    ('business_hours', 'business_hours'),
    ('integrations', 'integrations'),
    ('labels', 'labels'),
    ('quick_replies', 'quick_replies')
)

class Account(models.Model):
    account_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name
    
    
class CustomUser1(CustomUser):
    account_id = models.ForeignKey(Account, on_delete=models.CASCADE, null=True, blank=True)
    # team_id = models.ForeignKey(Team, on_delete=models.CASCADE, null=True, blank=True)
    role = models.CharField(choices=ROLE, max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.username

class Team(models.Model):
    team_id = models.AutoField(primary_key=True)
    account_id = models.ForeignKey(Account, on_delete=models.CASCADE)
    user_id = models.ManyToManyField(CustomUser1)
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name
  
class Contact(models.Model):
    contact_id = models.AutoField(primary_key=True)
    account_id = models.ForeignKey(Account, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=50)
    phone_number = models.BigIntegerField()
    email = models.EmailField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name
    
class Channle(models.Model):
    channle_id = models.AutoField(primary_key=True)
    account_id = models.ForeignKey(Account, on_delete=models.CASCADE)
    type_channle = models.CharField(choices=TYPE_CHANNLE, max_length=25)
    name = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name
    
class Conversation(models.Model):
    conversation_id = models.AutoField(primary_key=True)
    account_id = models.ForeignKey(Account, on_delete=models.CASCADE, null=True, blank=True)
    channle_id = models.ForeignKey(Channle, on_delete=models.CASCADE, null=True, blank=True)
    contact_id = models.ForeignKey(Contact, on_delete=models.CASCADE, null=True, blank=True)
    status = models.CharField(choices=STATUS, max_length=20, default='open')
    created_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f'conversation for contact {self.contact_id.name}'
    
    # @property
    # def last_message(self):
    #     message = self.chatmessage_set.filter().first().order_by('-created_at')
    #     return message.content
    
class ChatMessage(models.Model):
    message_id = models.AutoField(primary_key=True)
    conversation_id = models.ForeignKey(Conversation, on_delete=models.CASCADE)
    user_id = models.ForeignKey(CustomUser1, on_delete=models.CASCADE)
    content_type = models.CharField(choices=CONTENT_TYPE, max_length=20)
    content = models.TextField(max_length=1000)
    wamid = models.CharField(max_length=500)
    status_message = models.CharField(choices=STATUS_MESSAGE, max_length=20, default='sent')
    status_updated_at = models.DateTimeField(auto_now_add=True)
    media_url = models.URLField(null=True, blank=True)
    media_mime_type = models.CharField(max_length=50, null=True, blank=True)
    media_sha256_hash = models.CharField(max_length=256, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f'message {self.message_id}'
    
class MessageStatus(models.Model):
    status_id = models.AutoField(primary_key=True)
    message_id = models.ForeignKey(ChatMessage, on_delete=models.CASCADE)
    status = models.CharField(choices=STATUS_MESSAGE_STATUS, max_length=25)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f'message id {self.message_id.message_id} status is {self.status}'

class MediaManagement(models.Model):
    media_id = models.AutoField(primary_key=True)
    message_id = models.ForeignKey(ChatMessage, on_delete=models.CASCADE)
    media_url = models.URLField(null=True, blank=True)
    file_type = models.CharField(choices=CONTENT_TYPE, max_length=25, null=True, blank=True)
    mime_type = models.CharField(max_length=50, null=True, blank=True)
    size = models.BigIntegerField(null=True, blank=True)
    hash256_sha = models.CharField(max_length=256, null=True, blank=True)
    uploded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f'media management for message id {self.message_id.message_id}'
    
class Campaign(models.Model):
    campaign_id = models.AutoField(primary_key=True)
    account_id = models.ForeignKey(Account, on_delete=models.CASCADE, blank=True, null=True)
    name = models.CharField(max_length=50, null=True, blank=True)
    status = models.CharField(choices=STATUS_CAMPAIGN, max_length=20, default='active')
    start_date = models.DateField(auto_now_add=False)   
    end_date = models.DateField(auto_now_add=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f'campaign for account {self.account_id.name}'
    
class InternalChat(models.Model):
    caht_id = models.AutoField(primary_key=True)
    team_id = models.ForeignKey(Team, on_delete=models.CASCADE)
    user_id = models.ForeignKey(CustomUser1, on_delete=models.CASCADE)
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
    
