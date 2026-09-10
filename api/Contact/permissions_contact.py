from rest_framework.permissions import BasePermission


class ContactPermissions(BasePermission):
    """
    Custom permission class for Contact operations
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        if request.method == 'GET':
            return request.user.has_perm('api.view_contact')
        elif request.method == 'POST':
            return request.user.has_perm('api.add_contact')
        elif request.method in ['PUT', 'PATCH']:
            return request.user.has_perm('api.change_contact')
        elif request.method == 'DELETE':
            return request.user.has_perm('api.delete_contact')
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
            return request.user.has_perm('api.view_contact')
        elif request.method in ['PUT', 'PATCH']:
            return request.user.has_perm('api.change_contact')
        elif request.method == 'DELETE':
            return request.user.has_perm('api.delete_contact')
        return False


class ConversationPermissions(BasePermission):
    """
    Custom permission class for Conversation operations
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        if request.method == 'GET':
            return request.user.has_perm('api.view_contact')
        elif request.method in ['PUT', 'PATCH']:
            return request.user.has_perm('api.change_contact')
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
        
        return request.user.has_perm('api.view_contact')
