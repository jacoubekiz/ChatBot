# Generated by Django 5.1.3 on 2024-11-05 18:40

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='TestWebhook',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('test_text', models.CharField(max_length=50)),
                ('name', models.CharField(max_length=20)),
            ],
        ),
    ]
