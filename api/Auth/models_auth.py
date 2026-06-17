from django.db import models
from django.contrib.auth.models import AbstractUser
import secrets
# from .configure_api import *

ROLE_USER = (
    ('admin', 'admin'),
    ('sub-admin', 'sub-admin'),
    ('agent', 'agent')
)

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
    phonenumber = models.BigIntegerField(null=True, blank=True)
    role_user = models.CharField(choices=ROLE_USER, max_length=20, default='admin')
    manager = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='subordinates')

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username',]

    def __str__(self) -> str:
        return self.username
    
    class Meta:
        permissions = [
            ('can_access_chatBotBuilder', 'Can Access ChatBot Builder'),
            ('can_access_channels', 'Can Access Channels'),
            ('can_access_team_members', 'Can Access Team Members'),
            ('can_reassign_for_all_chat', 'can reassign for all chat'),
            ('can_reassign_for_own_chat', 'can reassign for own chat'),
            ('can_not_reassign', 'can not reassign'),
            ('visibility_all_conversations', 'visibility all conversations'),
            ('visibility_assigned_conversations', 'visibility assigned conversations'),
            ('can_access_developer', 'can access developer')
        ]


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
