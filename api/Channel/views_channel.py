from rest_framework.generics import (
    GenericAPIView,
    RetrieveUpdateDestroyAPIView,
    ListCreateAPIView
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from api.Channel.models_channel import Channle
from api.Channel.serializers_channel import ChannleSerializer
from api.Channel.permissions_channel import ChannelPermissions
from api.Account.models_account import Account

class ListCreateChannelView(ListCreateAPIView):
    
    serializer_class = ChannleSerializer
    permission_classes = [IsAuthenticated, ChannelPermissions]
    def get_queryset(self):
        account_id = self.kwargs['account_id']
        return Channle.objects.filter(account_id=account_id).select_related('account_id')
    
    def perform_create(self, serializer):
        account_id = Account.objects.get(account_id=self.kwargs['account_id'])
        serializer.save(account_id=account_id)
    
class RetrieveUpdateDeleteChannelView(RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, ChannelPermissions]
    serializer_class = ChannleSerializer
    lookup_field = 'account_id'
    def get_queryset(self):
        account_id = self.kwargs['account_id']
        channel = self.kwargs['channel_id']
        return Channle.objects.filter(account_id=account_id, channle_id=channel).select_related('account_id')

    def perform_update(self, serializer):
        account_id = get_object_or_404(Account, account_id=self.kwargs['account_id'])
        serializer.save(account_id=account_id)