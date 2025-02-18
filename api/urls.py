from django.urls import path, include
from .views import *
from rest_framework.routers import DefaultRouter

router = DefaultRouter()

router.register(r'clients', ClientsViewSet, basename='clients')

urlpatterns = [
    path('bot-api/', BotAPI.as_view(), name = 'bot_api'),
    path('', include(router.urls)),

    # path('get-redis/', GetData.as_view()),

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
    path('users/', ListCreateUserView.as_view(), name='users'),
    path('auth/login/', ViewLogin.as_view(), name='log-in'),
    path('auth/logout/', LogoutAPIView.as_view()),

    path('teams/', GetTeamView.as_view(), name='teams'),
    path('contacts/', ListContactView.as_view(), name='contacts'),
    path('conversations/<str:channel_id>/', ListConversationView.as_view(), name='conversations'),
    path('list-messages/<str:conversation_id>/', ListMessgesForSpecificConversation.as_view(), name='list-messages'),

    # path('get-data-from-redis/', GetDataFromRedis.as_view(), name='get-data-from-reis'),
    path('webhook/', WebhookView.as_view(), name='webhook'),

    path('convert-image-base64/', ImageToBase64View.as_view(), name='image_to_base64'),

    path('register-response-client/', RegisterResponseClient.as_view()),
]

