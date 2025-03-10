# Generated by Django 5.1.3 on 2024-11-17 11:19

import gdstorage.storage
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('webhook', '0003_remove_channle_account_id_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='MapFile',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('map_name', models.CharField(max_length=200)),
                ('map_data', models.FileField(storage=gdstorage.storage.GoogleDriveStorage(permissions=(gdstorage.storage.GoogleDriveFilePermission(gdstorage.storage.GoogleDrivePermissionRole['READER'], gdstorage.storage.GoogleDrivePermissionType['USER'], 'jacoubakizi87@gmail.com'),)), upload_to='maps')),
            ],
        ),
    ]
