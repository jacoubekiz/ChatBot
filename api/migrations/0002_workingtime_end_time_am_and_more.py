# Generated by Django 4.2.5 on 2024-09-04 06:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='workingtime',
            name='end_time_am',
            field=models.TimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='workingtime',
            name='starting_time_am',
            field=models.TimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='workingtime',
            name='starting_time_pm',
            field=models.TimeField(blank=True, null=True),
        ),
    ]
