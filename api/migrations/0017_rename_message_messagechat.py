# Generated by Django 4.2.5 on 2024-10-27 11:14

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0016_message'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Message',
            new_name='MessageChat',
        ),
    ]
