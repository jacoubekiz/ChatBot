from rest_framework.generics import (
    GenericAPIView, 
    RetrieveUpdateDestroyAPIView, 
    ListCreateAPIView
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from api.Account.models_account import Account
from api.Flow.models_flow import Trigger
from api.Contact.models_contact import Conversation
from api.Messaging.models_messaging import Group, QuickReply

from api.Messaging.serializers_messaging import (
    QuickReplySerializer, 
    TriggerSerializer, 
    GroupSerializer
)


class CreateListQuickReplyView(GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, account_id):
        data = request.data
        serializer = QuickReplySerializer(data=data, context={'account_id':account_id})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def get(self, request, account_id):
        account = get_object_or_404(Account, account_id=account_id)
        quick_replies = QuickReply.objects.filter(account_id=account)
        serializer = QuickReplySerializer(quick_replies, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RetrieveUpdateDeleteQuickReplyView(RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = QuickReplySerializer
    lookup_field = 'quickreply_id'

    def get_queryset(self):
        account = self.kwargs['account_id']
        quick_reply_id = self.kwargs['quickreply_id']
        return QuickReply.objects.filter(account_id=account, quickreply_id=quick_reply_id)
    
    def perform_update(self, serializer):
        account_id = get_object_or_404(Account, account_id=self.kwargs['account_id'])
        serializer.save(account_id=account_id)


class ListCreateTriggerView(GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, account_id):
        data = request.data
        serializer = TriggerSerializer(data=data, context={'account_id':account_id})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def get(self, request, account_id):
        account = get_object_or_404(Account, account_id=account_id)
        triggers = Trigger.objects.filter(account_id=account)
        serializer = TriggerSerializer(triggers, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    

class RetrieveUpdateDeleteTriggerView(RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TriggerSerializer
    lookup_field = 'id'

    def get_queryset(self):
        trigger_id = self.kwargs['id']
        account = self.kwargs['account_id']
        return Trigger.objects.filter(id=trigger_id, account_id=account)

    def perform_update(self, serializer):
        account = get_object_or_404(Account, account_id=self.kwargs['account_id'])
        serializer.save(account=account)


class ListCreateGroupView(ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = GroupSerializer
    queryset = Group.objects.all()
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['account_id'] = self.kwargs['account_id']
        tag = self.request.query_params.get('tag')
        members = Conversation.objects.filter(tags__tag_id=tag).values_list('contact_id', flat=True).distinct()
        if not members:
            return Response({'error':'No members found'}, status=status.HTTP_200_OK)
        context["members"] = members
        return context
    

class RetrieveUpdateDeleteGroupView(RetrieveUpdateDestroyAPIView):
    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated]
    queryset = Group.objects.all()
    lookup_field = 'id'

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['account_id'] = self.kwargs['account_id']
        tag = self.request.query_params.get('tag')
        members = Conversation.objects.filter(tags__tag_id=tag).values_list('contact_id', flat=True).distinct()
        if not members:
            return {'error':'No members found'}
        context["members"] = members
        return context
