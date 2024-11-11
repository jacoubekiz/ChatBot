from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied
from .models import CustomUser1

class UserIsAdmin(BasePermission):
    def has_permission(self, request, view):
        try:
            user = CustomUser1.objects.get(email=request.user.email)
        except:
            raise PermissionDenied("dont have permission")
        return bool(request.user and user.role == 'admin')