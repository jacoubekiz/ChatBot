# Generated by Django 5.1.3 on 2024-11-10 06:46

import datetime
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0017_rename_message_messagechat'),
    ]

    operations = [
        migrations.CreateModel(
            name='Account',
            fields=[
                ('account_id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=100)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='TestWebhook',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('test_text', models.CharField(max_length=50)),
                ('name', models.CharField(max_length=20)),
            ],
        ),
        migrations.RemoveField(
            model_name='customuser',
            name='phonenumber',
        ),
        migrations.AddField(
            model_name='customuser',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='customuser',
            name='role',
            field=models.CharField(choices=[('admin', 'admin'), ('agent', 'agent')], default='admin', max_length=20),
        ),
        migrations.AddField(
            model_name='customuser',
            name='updated_at',
            field=models.DateTimeField(auto_now_add=True, default=datetime.datetime(2024, 11, 10, 6, 46, 12, 288131, tzinfo=datetime.timezone.utc)),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='customuser',
            name='account_id',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='api.account'),
        ),
        migrations.CreateModel(
            name='Campaign',
            fields=[
                ('campaign_id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(blank=True, max_length=50, null=True)),
                ('status', models.CharField(choices=[('active', 'active'), ('inactive', 'inactive'), ('complated', 'complated')], max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now_add=True)),
                ('account_id', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.account')),
            ],
        ),
        migrations.CreateModel(
            name='Channle',
            fields=[
                ('channle_id', models.AutoField(primary_key=True, serialize=False)),
                ('type_channle', models.CharField(choices=[('WhatsApp', 'WhatsApp')], max_length=25)),
                ('name', models.CharField(max_length=50)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('account_id', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.account')),
            ],
        ),
        migrations.CreateModel(
            name='ChatbotBuilder',
            fields=[
                ('bot_id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(blank=True, max_length=50, null=True)),
                ('configuration', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('account_id', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.account')),
            ],
        ),
        migrations.CreateModel(
            name='Contact',
            fields=[
                ('contact_id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=50)),
                ('phone_number', models.BigIntegerField()),
                ('email', models.EmailField(max_length=254)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now_add=True)),
                ('account_id', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.account')),
            ],
        ),
        migrations.CreateModel(
            name='Conversation',
            fields=[
                ('conversation_id', models.AutoField(primary_key=True, serialize=False)),
                ('status', models.CharField(choices=[('open', 'open'), ('closed', 'closed'), ('pending', 'pending')], max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('account_id', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.account')),
                ('channle_id', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.channle')),
                ('contact_id', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.contact')),
            ],
        ),
        migrations.CreateModel(
            name='ChatMessage',
            fields=[
                ('message_id', models.AutoField(primary_key=True, serialize=False)),
                ('content_type', models.CharField(choices=[('text', 'text'), ('image', 'imgage'), ('video', 'video'), ('document', 'document'), ('audio', 'audio')], max_length=20)),
                ('content', models.TextField(max_length=1000)),
                ('wamid', models.CharField(max_length=500)),
                ('status_message', models.CharField(choices=[('sent', 'sent'), ('delivered', 'delivered'), ('read', 'read'), ('failed', 'failed'), ('pending', 'pending')], max_length=20)),
                ('status_updated_at', models.DateTimeField(auto_now_add=True)),
                ('media_url', models.URLField(blank=True, null=True)),
                ('media_mime_type', models.CharField(blank=True, max_length=50, null=True)),
                ('media_sha256_hash', models.CharField(blank=True, max_length=256, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now_add=True)),
                ('user_id', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('conversation_id', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.conversation')),
            ],
        ),
        migrations.CreateModel(
            name='MediaManagement',
            fields=[
                ('media_id', models.AutoField(primary_key=True, serialize=False)),
                ('media_url', models.URLField(blank=True, null=True)),
                ('file_type', models.CharField(blank=True, choices=[('text', 'text'), ('image', 'imgage'), ('video', 'video'), ('document', 'document'), ('audio', 'audio')], max_length=25, null=True)),
                ('mime_type', models.CharField(blank=True, max_length=50, null=True)),
                ('size', models.BigIntegerField(blank=True, null=True)),
                ('hash256_sha', models.CharField(blank=True, max_length=256, null=True)),
                ('uploded_at', models.DateTimeField(auto_now_add=True)),
                ('message_id', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.chatmessage')),
            ],
        ),
        migrations.CreateModel(
            name='MessageStatus',
            fields=[
                ('status_id', models.AutoField(primary_key=True, serialize=False)),
                ('status', models.CharField(choices=[('sent', 'sent'), ('delivered', 'delivered'), ('read', 'read')], max_length=25)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('message_id', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.chatmessage')),
            ],
        ),
        migrations.CreateModel(
            name='Report',
            fields=[
                ('report_id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(blank=True, max_length=50, null=True)),
                ('data', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('account_id', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.account')),
            ],
        ),
        migrations.CreateModel(
            name='Setting',
            fields=[
                ('setting_id', models.AutoField(primary_key=True, serialize=False)),
                ('type_setting', models.CharField(blank=True, choices=[('business_hours', 'business_hours'), ('integrations', 'integrations'), ('labels', 'labels'), ('quick_replies', 'quick_replies')], max_length=50, null=True)),
                ('config_data', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now_add=True)),
                ('account_id', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.account')),
            ],
        ),
        migrations.CreateModel(
            name='Team',
            fields=[
                ('team_id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=100)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now_add=True)),
                ('account_id', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.account')),
            ],
        ),
        migrations.CreateModel(
            name='InternalChat',
            fields=[
                ('caht_id', models.AutoField(primary_key=True, serialize=False)),
                ('content', models.TextField(blank=True, null=True)),
                ('sent_at', models.DateTimeField(auto_now_add=True)),
                ('user_id', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('team_id', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.team')),
            ],
        ),
        migrations.AddField(
            model_name='customuser',
            name='team_id',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='api.team'),
        ),
    ]
