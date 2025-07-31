# from django.db import models
# # from django.contrib.auth.models import AbstractBaseUser
# # from api.models import CustomUser

# from gdstorage.storage import GoogleDriveStorage

# from gdstorage.storage import GoogleDriveStorage, GoogleDrivePermissionType, GoogleDrivePermissionRole, GoogleDriveFilePermission

# permission =  GoogleDriveFilePermission(
#    GoogleDrivePermissionRole.READER,
#    GoogleDrivePermissionType.USER,
#    "jacoubakizi87@gmail.com"
# )
# # Define Google Drive Storage
# gd_storage = GoogleDriveStorage(permissions=(permission, ))

# class MapFile(models.Model):
#     id = models.AutoField( primary_key=True)
#     map_name = models.CharField(max_length=200)
#     map_data = models.FileField(upload_to='maps', storage=gd_storage)
