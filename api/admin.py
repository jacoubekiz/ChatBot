from django.contrib import admin
from .models import  *
from .forms import CustomUserChangeForm, CustomUserCreationForm
from django.contrib.auth.admin import UserAdmin



class CustomUserAdmin(UserAdmin):

    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser

    list_display = ['username','id' ,'email', 'first_name', 'last_name', 'is_staff']
    fieldsets = (
    (None, 
         {'fields':('email', 'password',)}
     ),
    ('User Information',
        {'fields':('username', 'first_name', 'last_name')}
    ),
    ('Permissions', 
        {'fields':('is_staff', 'is_superuser', 'is_active', 'groups','user_permissions')}
    ),
    ('Registration', 
        {'fields':('date_joined', 'last_login',)}
    )
    )
    add_fieldsets = (
        (None, {'classes':('wide',),
            'fields':(
                'email', 'phonenumber', 'username', 'password1', 'password2',
            )}
            ),
        )
    search_fields = ("email",)
    ordering = ("email",)









class RestartKeywordInline(admin.TabularInline):

    model = RestartKeyword
    min_num = 1
    max_num = 10
    extra = 2

class ClientAdmin(admin.ModelAdmin):
    list_display = ['name', 'id', 'client_endpoint']
    search_fields = ['name']
    inlines = [RestartKeywordInline]
    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ['id', 'client_endpoint']
        else:
            return []
        
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Client, ClientAdmin)
admin.site.register(Chat)
admin.site.register(Attribute)
admin.site.register(Duration)
admin.site.register(Calendar)
admin.site.register(BookAnAppointment)
admin.site.register(WorkingTime)


admin.site.register(Trigger)
admin.site.register(Flow)
admin.site.site_title = "ICSL Bot Creator"
admin.site.site_header = "ICSL Bot Creator"