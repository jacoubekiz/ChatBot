from django.urls import path, include

urlpatterns = [
    # Authentication URLs
    path('', include('api.Auth.urls_auth')),
    
    # Account Management URLs
    path('', include('api.Account.urls_account')),
    
    # Team Management URLs
    path('', include('api.Team.urls_team')),
    
    # Flow Management URLs
    path('', include('api.Flow.urls_flow')),
    
    # Contact and Conversation URLs
    path('', include('api.Contact.urls_contact')),
    
    # Template Management URLs
    path('', include('api.handel_templates.urls_template')),
    
    # Campaign Management URLs
    path('', include('api.Campaign.urls_campaign')),
    
    # API Management URLs
    path('', include('api.APIs.urls_api')),
    
    # Messaging URLs (Quick Replies, Triggers, Groups)
    path('', include('api.Messaging.urls_messaging')),
    
    # Utility URLs (Webhook, Tags, etc.)
    path('', include('api.Utility.urls_utility')),
]

