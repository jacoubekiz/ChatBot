from django.core.management.base import BaseCommand
from django.utils import timezone
from api.models import Chat
import datetime

class Command(BaseCommand):
    help = 'Cleanup Chat instances that have not changed state in the last hour'

    def handle(self, *args, **options):
        now = timezone.now()

        chats_to_reset = Chat.objects.filter(client__resetting_minutes__isnull=False)
        for chat in chats_to_reset:
            reset_time = chat.last_state_change + datetime.timedelta(minutes=chat.client.resetting_minutes)
            if reset_time <= now:
                self.stdout.write(self.style.SUCCESS(f'Resetting Chat: {chat.conversation_id}'))
                chat.delete()