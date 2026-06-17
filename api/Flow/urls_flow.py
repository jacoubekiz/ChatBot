from django.urls import path
from .views_flow import (
    AddListFlows,
    UpdateFlowView,
    SetDefaultFlow,
    RetrieveFlow,
)

urlpatterns = [
    path('create-flow/<str:channel_id>/', AddListFlows.as_view(), name='create_flow'),
    path('update-flow/<str:pk>/', UpdateFlowView.as_view(), name='update_flow'),
    path('set-default-flow/<str:channel_id>/', SetDefaultFlow.as_view(), name='set_default_flow'),
    path('retrieve-flow/<str:pk>/', RetrieveFlow.as_view(), name='retrieve_flow'),
]
