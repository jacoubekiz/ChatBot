# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from .models import *

# @receiver(post_save, sender=ChatMessage)
# def bootstrap_status(sender, instance, created, **kwargs):
#     if not created:
#         return
#     recips = ChatMessage.objects.filter