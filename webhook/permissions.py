# from rest_framework.permissions import BasePermission
# from .models import Custom2User

# # class YourCustomPermission(BasePermission):
# #     def has_permission(self, request, view, user_id):
# #         # Use the user_id to make your permission decision
# #         # For example:
# #         # user = Custom2User.objects.get(pk=user_id)
# #         return user_id  # Only allow users with ID 1
        
# #     def has_object_permission(self, request, view, obj):
# #         # You can also override this method if needed
# #         return True
    
# class UserIsAdmin(BasePermission):
#     def has_permission(self, request, view):
#         user_id = request.pk
#         user = Custom2User.objects.get(pk=user_id)
#         return bool(request.user) and self.has_permission(request, view, user_id)
    
#     # def has_object_permission(self, request, view, obj):
#     #     return True