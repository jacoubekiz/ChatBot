from rest_framework.permissions import BasePermission


class TagPermissions(BasePermission):
    """
    Custom permission class for Tag operations
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        if request.method == 'GET':
            return request.user.has_perm('api.view_tag')
        elif request.method == 'POST':
            return request.user.has_perm('api.add_tag')
        elif request.method in ['PUT', 'PATCH']:
            return request.user.has_perm('api.change_tag')
        elif request.method == 'DELETE':
            return request.user.has_perm('api.delete_tag')
        return False
    
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        # Check if user has access to the account
        if hasattr(obj, 'account_id') and obj.account_id:
            if obj.account_id != request.user.account_set.first():
                return False
        
        if request.method == 'GET':
            return request.user.has_perm('api.view_tag')
        elif request.method in ['PUT', 'PATCH']:
            return request.user.has_perm('api.change_tag')
        elif request.method == 'DELETE':
            return request.user.has_perm('api.delete_tag')
        return False


class GroupPermissions(BasePermission):
    """
    Custom permission class for Group operations
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        if request.method == 'GET':
            return request.user.has_perm('api.view_group')
        elif request.method == 'POST':
            return request.user.has_perm('api.add_group')
        elif request.method in ['PUT', 'PATCH']:
            return request.user.has_perm('api.change_group')
        elif request.method == 'DELETE':
            return request.user.has_perm('api.delete_group')
        return False
    
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        # Check if user has access to the account
        if hasattr(obj, 'account') and obj.account:
            if obj.account != request.user.account_set.first():
                return False
        
        if request.method == 'GET':
            return request.user.has_perm('api.view_group')
        elif request.method in ['PUT', 'PATCH']:
            return request.user.has_perm('api.change_group')
        elif request.method == 'DELETE':
            return request.user.has_perm('api.delete_group')
        return False


class QuickReplyPermissions(BasePermission):
    """
    Custom permission class for QuickReply operations
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        if request.method == 'GET':
            return request.user.has_perm('api.view_quick_reply')
        elif request.method == 'POST':
            return request.user.has_perm('api.add_quick_reply')
        elif request.method in ['PUT', 'PATCH']:
            return request.user.has_perm('api.change_quick_reply')
        elif request.method == 'DELETE':
            return request.user.has_perm('api.delete_quick_reply')
        return False
    
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        # Check if user has access to the account
        if hasattr(obj, 'account_id') and obj.account_id:
            if obj.account_id != request.user.account_set.first():
                return False
        
        if request.method == 'GET':
            return request.user.has_perm('api.view_quick_reply')
        elif request.method in ['PUT', 'PATCH']:
            return request.user.has_perm('api.change_quick_reply')
        elif request.method == 'DELETE':
            return request.user.has_perm('api.delete_quick_reply')
        return False
