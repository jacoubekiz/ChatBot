from rest_framework.permissions import BasePermission
from api.Account.models_account import Account

class ChannelPermissions(BasePermission):
    """
    Custom permission class for Channel operations
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Allow superusers
        
        if request.user.is_superuser:
            return True
        
        if request.method == 'GET':
            return request.user.has_perm('api.view_channle')
        elif request.method == 'POST':
            return request.user.has_perm('api.add_channle')
        elif request.method in ['PUT', 'PATCH']:
            return request.user.has_perm('api.change_channle')
        elif request.method == 'DELETE':
            print(request.user.has_perm('api.delete_channle'))
            return request.user.has_perm('api.delete_channle')
        return False
    
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Allow superusers
        if request.user.is_superuser:
            return True
        
        # Check if user has access to the account
        if hasattr(obj, 'account_id') and obj.account_id:
            user_account = Account.objects.filter(user=request.user.manager.id).first()
            if not user_account or obj.account_id.account_id != user_account.account_id:
                return False
        
        if request.method == 'GET':
            return request.user.has_perm('api.view_channle')
        elif request.method in ['PUT', 'PATCH']:
            return request.user.has_perm('api.change_channle')
        elif request.method == 'DELETE':
            return request.user.has_perm('api.delete_channle')
        return False
