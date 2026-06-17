from django.urls import path
from .views_campaign import (
    # HandelCSView,
    CreateListCampaignsView,
    GetCampaignView
)

urlpatterns = [
    # path('handle-csv-file/', HandelCSView.as_view(), name='handle_csv_file'),
    path('campaigns/<str:channel_id>/', CreateListCampaignsView.as_view(), name='create_compaingn'),
    path('get-campaign/<str:campaign_id>/', GetCampaignView.as_view(), name='get_campaign'),
]
