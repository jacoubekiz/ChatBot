from rest_framework.generics import (
    ListCreateAPIView, 
    RetrieveUpdateDestroyAPIView
)
from rest_framework.permissions import IsAuthenticated
from api.Account.models_account import Account
from api.Channel.models_channel import Channle
from api.Channel.serializers_channel import ChannleSerializer


class ListCreateChannelView(ListCreateAPIView):
    
    serializer_class = ChannleSerializer
    permission_classes = [IsAuthenticated,]
    def get_queryset(self):
        account_id = self.kwargs['account_id']
        return Channle.objects.filter(account_id=account_id)
    
    def perform_create(self, serializer):
        account_id = Account.objects.get(account_id=self.kwargs['account_id'])
        serializer.save(account_id=account_id)
    
class RetrieveUpdateDeleteChannelView(RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated,]
    serializer_class = ChannleSerializer
    lookup_field = 'account_id'
    def get_queryset(self):
        account_id = self.kwargs['account_id']
        channel = self.kwargs['channel_id']
        return Channle.objects.filter(account_id=account_id, channle_id=channel)

    def perform_update(self, serializer):
        account_id = get_object_or_404(Account, account_id=self.kwargs['account_id'])
        serializer.save(account_id=account_id)