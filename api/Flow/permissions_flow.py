from rest_framework.permissions import BasePermission


class FlowPermissions(BasePermission):
    """
    Custom permission class for Flow operations
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        if request.method == 'GET':
            print(request.user.user_permissions)
            return request.user.has_perm('api.view_flow')
        elif request.method == 'POST':
            return request.user.has_perm('api.add_flow')
        elif request.method in ['PUT', 'PATCH']:
            return request.user.has_perm('api.change_flow')
        elif request.method == 'DELETE':
            return request.user.has_perm('api.delete_flow')
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
            return request.user.has_perm('api.view_flow')
        elif request.method in ['PUT', 'PATCH']:
            return request.user.has_perm('api.change_flow')
        elif request.method == 'DELETE':
            return request.user.has_perm('api.delete_flow')
        return False


class SetDefaultFlowPermission(BasePermission):
    """
    Permission for setting default flow
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        return request.user.has_perm('api.can_set_default_flow')
