from django.urls import path, include
from .views import *
from rest_framework.routers import DefaultRouter
from .handel_templates.views import *

router = DefaultRouter()

# router.register(r'clients', ClientsViewSet, basename='clients')

urlpatterns = [
    path('bot-api/', BotAPI.as_view(), name = 'bot_api'),
    path('create-calander/', CreateCalenderView.as_view(), name='create-calander'),
    path('get-calander/<str:user_id>/', GetCalenderView.as_view(), name='get-calander'),
    path('get-hours-free/', GetHoursFree.as_view(), name='get-hours-free'),
    path('create-working-time/', CreateWorkingTimeView.as_view(), name='create-working-time'),
    path('create-book-an-appointment/', CreateBookAnAppointmentView.as_view(), name='create-an-appointment'),
    path('lsit-calendar-for-user/<str:calender_key>/', GetCalendarForUserView.as_view(), name='lsit-days-work-for-user'),
    path('get-first-ten-days/', GetFirstTenDays.as_view(), name='get-first-ten-days'),
    # path('get-doctors/', GetDoctorsView.as_view(), name='get-doctors'),
    path('get-doctors-calander/<str:doctor_id>/', GetDoctorsCalanderView.as_view(), name='get-doctors-calander'),
    path('send-email/', SendEmailView.as_view(), name='send-email'),

# add new api
    path('assign-role/<user_id>/', AssigningPermissions.as_view(), name='assign_role'),
    path('add-account/', CreateListAccount.as_view(), name='add_account'),
    path('update-delete-account/<str:pk>/', RetrieveUpdateDeleteAccount.as_view(), name='update_delete_account'),
    path('add-channel/<str:account_id>/', ListCreateChannelView.as_view(), name='add_channel'),
    path('update-delete-channel/<str:account_id>/<str:channel_id>/', RetrieveUpdateDeleteChannelView.as_view(), name='update_delete_channel'),
    path('add-team-member/<str:team_id>/', ListCreateTeamMemberView.as_view(), name='users'),
    path('list-team-member/<str:account_id>/', ListTeamMember.as_view(), name='team_members'),
    path('update-delete-team-member/<str:pk>/<str:team_id>/', RetrieveUpdateDeleteTeamMemberView.as_view(), name='update_delete_team_member'),
    path('list-all-members/<str:account_id>/', ListAllTeamMembers.as_view(), name='List_all_team_members'),
    path('create-flow/<str:channel_id>/', AddListFlows.as_view(), name='create_flow'),
    path('set-default-flow/<str:channel_id>/', SetDefaultFlow.as_view(), name='set_default_flow'),
    path('retrieve-flow/<str:pk>', RetrieveFlow.as_view(), name='retrieve_flow'),
    path('auth/login/', ViewLogin.as_view(), name='log-in'),
    path('auth/logout/', LogoutAPIView.as_view()),
    path('user-profile/<str:id>/', UserProfileView.as_view(), name='user_profile'),

    path('add-team/<account_id>/', ListCreateTeamView.as_view(), name='teams'),
    path('update-delete-team/<str:team_id>/<str:account_id>/', RetrieveUpdateDeleteTeamView.as_view(), name='update_delete_team'),
    path('create-contact/<account_id>/<channel_id>/', CreateNewContact.as_view(), name='create_contact'),
    path('update-delete-contact/<str:contact_id>/', RetrieveUpdateDestroyContactView.as_view(), name='update_delete_contact'),
    path('contacts/', ListContactView.as_view(), name='contacts'),
    path('conversations/<str:channel_id>/', ListConversationView.as_view(), name='conversations'),
    path('reassign-conversation/<str:conversation_id>/', ReasignConversation.as_view(), name='reassign_conversation'),
    path('list-messages/<str:conversation_id>/', ListMessgesForSpecificConversation.as_view(), name='list-messages'),
    path('initite-live-chat/<str:conversation_id>/', InitiateLiveChat.as_view(), name='initite_live_chat'),
    # path('get-data-from-redis/', GetDataFromRedis.as_view(), name='get-data-from-reis'),
    path('webhook/', WebhookView.as_view(), name='webhook'),
    path('convert-image-base64/', ImageToBase64View.as_view(), name='image_to_base64'),
    path('register-response-client/', RegisterResponseClient.as_view()),
    path('create-template/<str:channel_id>/', ListCreateTemplate.as_view(), name='create-template'),
    path('handle-file-upload/<str:channel_id>/', HandleFileUpload.as_view(), name='handle-file-upload'),
    path('get-template/', GetTemplate.as_view(), name='get-template'),
    path('send-template/<str:channel_id>/', SendTemplate.as_view(), name='send_template'),
    path('file-upload/<str:channel_id>/', FileUploadView.as_view(), name='file-upload'),
    path('change-conversation-status/<str:conversation_id>/', ChangeConversationStatus.as_view(), name='change_conversation_status'),
    path('tags/<str:account_id>/', CreateTagView.as_view(), name='create_tag'),
    path('add-tag-to-conversation/<str:conversation_id>/', AddTagToConversation.as_view(), name='add_tag_to_conversation'),
    path('change-password/<str:user_id>/', ChangePasswordView.as_view(), name='change_password'),

    path('handle-csv-file/', HandelCSView.as_view(), name='handle_csv_file'),
    path('Campaigns/<str:channel_id>/', CreateListCampaignsView.as_view(), name='create_compaingn'),
    path('apis/<str:account_id>/', ListCreateAPIView.as_view(), name='create_api'),
    path('delete-api/<str:api_id>/', DeleteAPIView.as_view(), name='delete_api'),
    path('delete-parameter/<str:parameter_id>/', DeleteParameterAPIView.as_view(), name='delete_parameter'),
    # path('quick-replies/<str:account_id>/', ggg.as_view(), name='quick_replies'),
    path('quick-reply/<str:account_id>/', CreateListQuickReplyView.as_view(), name='quick_replies'),
    path('delete-retriev-update-quick-reply/<str:quickreply_id>/<str:account_id>/', RetrieveUpdateDeleteQuickReplyView.as_view(), name='delete_quick_reply'),
    path('triggers/<str:account_id>/', ListCreateTriggerView.as_view(), name='triggers'),
    path('delete-retriev-update-trigger/<str:id>/<str:account_id>/', RetrieveUpdateDeleteTriggerView.as_view(), name='delete_trigger'),
]

