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
    phonenumber = models.BigIntegerField(unique=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username','phonenumber']

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