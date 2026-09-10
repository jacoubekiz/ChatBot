from rest_framework.permissions import BasePermission


class AccountPermissions(BasePermission):
    """
    Custom permission class for Account operations
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        if request.method == 'GET':
            return request.user.has_perm('api.view_account')
        elif request.method == 'POST':
            return request.user.has_perm('api.add_account')
        elif request.method in ['PUT', 'PATCH']:
            return request.user.has_perm('api.change_account')
        elif request.method == 'DELETE':
            return request.user.has_perm('api.delete_account')
        return False
    
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        # Check if user has access to the account
        if hasattr(obj, 'user') and obj.user:
            if obj.user != request.user:
                return False
        
        if request.method == 'GET':
            return request.user.has_perm('api.view_account')
        elif request.method in ['PUT', 'PATCH']:
            return request.user.has_perm('api.change_account')
        elif request.method == 'DELETE':
            return request.user.has_perm('api.delete_account')
        return False


class TeamPermissions(BasePermission):
    """
    Custom permission class for Team operations
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        if request.method == 'GET':
            return request.user.has_perm('api.view_team')
        elif request.method == 'POST':
            return request.user.has_perm('api.add_team')
        elif request.method in ['PUT', 'PATCH']:
            return request.user.has_perm('api.change_team')
        elif request.method == 'DELETE':
            return request.user.has_perm('api.delete_team')
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
            return request.user.has_perm('api.view_team')
        elif request.method in ['PUT', 'PATCH']:
            return request.user.has_perm('api.change_team')
        elif request.method == 'DELETE':
            return request.user.has_perm('api.delete_team')
        return False


class TeamMemberPermissions(BasePermission):
    """
    Custom permission class for Team member management
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        return request.user.has_perm('api.can_manage_team_members')
