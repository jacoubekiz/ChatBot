# Generated by Django 4.2.5 on 2024-09-26 08:13

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0010_bookanappointment_patient'),
    ]

    operations = [
        migrations.RenameField(
            model_name='bookanappointment',
            old_name='description',
            new_name='details',
        ),
        migrations.RenameField(
            model_name='bookanappointment',
            old_name='patient',
            new_name='patientName',
        ),
    ]