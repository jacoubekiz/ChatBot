from django.urls import path
from .views_account import (
    CreateListAccount,
    RetrieveUpdateDeleteAccount,
    GenerateapiKeyView
)

urlpatterns = [
    path('add-account/', CreateListAccount.as_view(), name='add_account'),
    path('update-delete-account/<str:pk>/', RetrieveUpdateDeleteAccount.as_view(), name='update_delete_account'),
    path('generate-apiKey/<str:account_id>/', GenerateapiKeyView.as_view(), name='generate_apiKey'),
]
