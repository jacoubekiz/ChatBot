# Generated by Django 5.1.3 on 2025-06-22 11:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0035_alter_customuser_options'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customuser',
            name='phonenumber',
            field=models.BigIntegerField(blank=True, default=352353525, null=True),
        ),
    ]
