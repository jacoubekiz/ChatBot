# Generated by Django 4.2.5 on 2024-10-17 08:05

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0012_flow_is_default_alter_bookanappointment_patientname_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='NextTime',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('time', models.TimeField()),
                ('chat', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.chat')),
            ],
        ),
        migrations.CreateModel(
            name='NextTenDay',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('day', models.DateField()),
                ('chat', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.chat')),
            ],
        ),
    ]