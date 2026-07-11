from django.contrib import admin
from api.Core.forms import CustomUserChangeForm, CustomUserCreationForm
from django.contrib.auth.admin import UserAdmin
# from .handel_time import get_day_name
from api.Account.models_account import Account, Team
from api.APIs.models_api import (
    Parameter, 
    API, 
    Api_parameter, 
    APILog
)
from api.Auth.models_auth import (
    CustomUser, 
    Duration, 
    WorkingTime, 
    Calendar, 
    BookAnAppointment
)
from api.Channel.models_channel import Channle
from api.Contact.models_contact import (
    Contact, 
    Conversation, 
    ChatMessage, 
    MessageStatus, 
    MediaManagement
)
from api.Flow.models_flow import (
    Flow, 
    Trigger, 
    Chat, 
    Attribute, 
    Custome_attribute, 
    RestartKeyword
)
from api.Messaging.models_messaging import Tag, Group, QuickReply
from api.Utility.models_utility import (
    TestWebhook, 
    InternalChat, 
    Report, 
    ChatbotBuilder, 
    Setting, 
    UploadImage
)
from api.Campaign.models_campaign import WhatsAppCampaign, AnalyticsCampaign
from api.handel_templates.models_template import Template, TemplateBox, TemplateBoxTemplate


class CustomUserAdmin(UserAdmin):

    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser

    list_display = ['username','id' ,'email', 'first_name', 'last_name', 'is_staff', 'role_user', 'manager']
    fieldsets = (
    (None, 
         {'fields':('email', 'password',)}
     ),
    ('User Information',
        {'fields':('username', 'first_name', 'last_name',)}
    ),
    ('Permissions', 
        {'fields':('is_staff', 'is_superuser', 'is_active', 'groups','user_permissions', 'role_user')}
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

# class ClientAdmin(admin.ModelAdmin):
#     list_display = ['name', 'id', 'client_endpoint']
#     search_fields = ['name']
#     inlines = [RestartKeywordInline]
#     def get_readonly_fields(self, request, obj=None):
#         if obj:
#             return ['id', 'client_endpoint']
#         else:
#             return []

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

class FlowAdmin(admin.ModelAdmin):
    list_display = ['id', 'account', 'flow_name', 'is_default']

class AccountAdmin(admin.ModelAdmin):
    list_display = ['account_id', 'name', 'user', 'apiKey', 'created_at']

class AttributeAdmin(admin.ModelAdmin):
    list_display = ['account_name', 'key']

    def account_name(self, obj):
        return obj.account.name
    
class Custome_attributeAdmin(admin.ModelAdmin):
    list_display = ['account', 'key', 'value', 'contact']

    def account(self, obj):
        return obj.attribute.account.name
    
    def key(self, obj):
        return obj.attribute.key
    
    def contact(self, obj):
        conversation = Conversation.objects.filter(contact_id__phone_number=obj.chat.conversation_id).first()
        contact_name = conversation.contact_id.name or conversation.contact_id.phone_number if conversation else None
        return contact_name 

class CompaignAdmin(admin.ModelAdmin):
    list_display = ['campaign_id', 'name', 'account', 'status', 'template_name', 'total_recipients', 'failed_count', 'sent_count']  

    def account(self, obj):
        return obj.account_id.name
admin.site.register(WhatsAppCampaign, CompaignAdmin)
admin.site.register(Custome_attribute, Custome_attributeAdmin)
admin.site.register(CustomUser, CustomUserAdmin)
# admin.site.register(Client, ClientAdmin)
admin.site.register(Chat)
admin.site.register(Attribute, AttributeAdmin)
admin.site.register(Duration)
admin.site.register(Calendar)
admin.site.register(BookAnAppointment, BookAnAppointmentAdmin)
admin.site.register(WorkingTime)
admin.site.register(RestartKeyword)
# admin.site.register(NextTime)
# admin.site.register(MessageChat)

admin.site.register(Trigger)
admin.site.register(Flow, FlowAdmin)
admin.site.site_title = "ICSL Bot Creator"
admin.site.site_header = "ICSL Bot Creator"
admin.site.register(UploadImage, UploadImageAdmin)
admin.site.register(Contact)
admin.site.register(Conversation)
admin.site.register(Team)
admin.site.register(ChatMessage, ChatMessageAdmin)
admin.site.register(Account, AccountAdmin)
admin.site.register(Channle)
admin.site.register(API)
admin.site.register(Parameter)
admin.site.register(Api_parameter)
admin.site.register(QuickReply)
admin.site.register(Tag)
admin.site.register(AnalyticsCampaign)
admin.site.register(Group)
admin.site.register(APILog)
admin.site.register(Template)
admin.site.register(TemplateBox)
admin.site.register(TemplateBoxTemplate)