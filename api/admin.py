from django.contrib import admin
from .models import  *
from .forms import CustomUserChangeForm, CustomUserCreationForm
from django.contrib.auth.admin import UserAdmin
from .handel_time import get_day_name

# @admin.register(CustomUser1)
# class CustomUser1Admin(admin.ModelAdmin):
#     list_display = ('email', 'username', 'first_name', 'last_name', 'is_staff')
#     search_fields = ('email', 'username', 'first_name', 'last_name')
#     ordering = ('email',)


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
        {'fields':('username', 'first_name', 'last_name',)}
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
                'email', 'username', 'password1', 'password2',
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

class BookAnAppointmentAdmin(admin.ModelAdmin):
    list_display = ['doctor','days', 'duration', 'hour', 'patientName']
    search_fields = ['doctor', 'patientName']

    list_filter = ['is_proccessed']
    def doctor(self, obj):
        return obj.user.username
    def days(self, obj):
        return get_day_name(obj.day)

class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['message_id', 'content','caption' , 'content_type', 'from_message']

class UploadImageAdmin(admin.ModelAdmin):
    list_display = ['id', 'image_file']

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Client, ClientAdmin)
admin.site.register(Chat)
admin.site.register(Attribute)
admin.site.register(Duration)
admin.site.register(Calendar)
admin.site.register(BookAnAppointment, BookAnAppointmentAdmin)
admin.site.register(WorkingTime)
admin.site.register(NextTenDay)
admin.site.register(NextTime)
admin.site.register(MessageChat)

admin.site.register(Trigger)
admin.site.register(Flow)
admin.site.site_title = "ICSL Bot Creator"
admin.site.site_header = "ICSL Bot Creator"




admin.site.register(UploadImage, UploadImageAdmin)

admin.site.register(Contact)
admin.site.register(Conversation)
admin.site.register(Team)
# admin.site.register(Account)
admin.site.register(ChatMessage, ChatMessageAdmin)
admin.site.register(Account)
admin.site.register(Channle)