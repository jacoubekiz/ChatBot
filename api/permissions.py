from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied
from .models import CustomUser

class UserIsAdmin(BasePermission):
    def has_permission(self, request, view):
        try:
            user = CustomUser.objects.get(email=request.user.email)
        except:
            raise PermissionDenied("dont have permission")
        return bool(request.user and user.role_user == 'admin')
    
class AccessChatBuilder(BasePermission):
    def has_permission(self, request, view):
        try:
            user = CustomUser.objects.get(email=request.user.email)
        except:
            raise PermissionDenied("dont have permission")
        return bool(request.user and user.has_perm('can_access_chatBotBuilder'))
    
class AccessChannels(BasePermission):
    def has_permission(self, request, view):
        try:
            user = CustomUser.objects.get(email=request.user.email)
        except:
            raise PermissionDenied("dont have permission")
        return bool(request.user and user.has_perm('can_access_channels'))
    
class AccessTeamMembers(BasePermission):
    def has_permission(self, request, view):
        try:
            user = CustomUser.objects.get(email=request.user.email)
        except:
            raise PermissionDenied("dont have permission")
        return bool(request.user and user.has_perm('can_access_team_members'))