# Generated by Django 5.1.3 on 2024-11-17 06:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0024_alter_contact_email'),
    ]

    operations = [
        migrations.AlterField(
            model_name='chatmessage',
            name='status_message',
            field=models.CharField(choices=[('sent', 'sent'), ('delivered', 'delivered'), ('read', 'read'), ('failed', 'failed'), ('pending', 'pending')], default='sent', max_length=20),
        ),
    ]
