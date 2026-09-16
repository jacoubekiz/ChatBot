from rest_framework.permissions import BasePermission


class CampaignPermissions(BasePermission):
    """
    Custom permission class for Campaign operations
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        if request.method == 'GET':
            return request.user.has_perm('api.view_whatsappcampaign')
        elif request.method == 'POST':
            return request.user.has_perm('api.add_whatsappcampaign')
        elif request.method in ['PUT', 'PATCH']:
            return request.user.has_perm('api.change_whatsappcampaign')
        elif request.method == 'DELETE':
            return request.user.has_perm('api.delete_whatsappcampaign')
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
            return request.user.has_perm('api.view_whatsappcampaign')
        elif request.method in ['PUT', 'PATCH']:
            return request.user.has_perm('api.change_whatsappcampaign')
        elif request.method == 'DELETE':
            return request.user.has_perm('api.delete_whatsappcampaign')
        return False
