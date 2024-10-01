# Generated by Django 4.2.5 on 2024-09-28 06:43

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0011_rename_description_bookanappointment_details_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='flow',
            name='is_default',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='bookanappointment',
            name='patientName',
            field=models.CharField(max_length=50),
        ),
        migrations.AlterField(
            model_name='chat',
            name='flow',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.flow'),
        ),
        migrations.AlterField(
            model_name='flow',
            name='trigger',
            field=models.ManyToManyField(blank=True, null=True, to='api.trigger'),
        ),
    ]