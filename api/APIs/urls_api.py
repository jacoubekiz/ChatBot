from django.urls import path
from .views_api import (
    ListCreateApiView,
    UpdateApiview,
    GetApiView,
    SaveResponse,
    ListCreateAttributeView,
    DeleteAPIView,
    DeleteParameterAPIView,
    APILogVeiw,
    RetAupDelAttributeView
)

urlpatterns = [
    path('apis/<str:account_id>/', ListCreateApiView.as_view(), name='create_api'),
    path('update-api/<str:api_id>/<str:account_id>/', UpdateApiview.as_view(), name='retrive_update_api'),
    path('retrieve-api/<str:api_id>/', GetApiView.as_view(), name='retrieve_api'),
    path('save-response/<str:api_id>/', SaveResponse.as_view(), name='save_response'),
    path('list-create-attribute/<str:account_id>/', ListCreateAttributeView.as_view(), name='list_create_attribute'),
    path('delete-api/<str:api_id>/', DeleteAPIView.as_view(), name='delete_api'),
    path('delete-parameter/<str:parameter_id>/', DeleteParameterAPIView.as_view(), name='delete_parameter'),
    path('list-create-apilog/<str:api_id>/', APILogVeiw.as_view(), name='list_create_apilog'),
    path('delete-retriev-update-attribute/<str:id>/<str:account_id>/', RetAupDelAttributeView.as_view(), name='delete_attribute'),
]
