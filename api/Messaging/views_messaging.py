import base64
from rest_framework.generics import (
    GenericAPIView, 
    RetrieveUpdateDestroyAPIView, 
    ListCreateAPIView
)
from api.Core.pagination import CustomPaginatins
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from api.Account.models_account import Account
from api.Flow.models_flow import Trigger
from api.Contact.models_contact import Conversation
from api.Messaging.models_messaging import Group, QuickReply, Tag
from api.Messaging.serializers_messaging import (
    QuickReplySerializer, 
    TriggerSerializer, 
    GroupSerializer,
    TagSerializer
)

class CreateTagView(GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, account_id):
        name = request.data['name']
        account = get_object_or_404(Account, account_id=account_id)
        tag = Tag.objects.create(
            name=name,
            account_id=account
        )
        return Response({'tag_id': tag.tag_id, 'name': tag.name}, status=status.HTTP_201_CREATED)
    
    def get(self, request, account_id):
        account = get_object_or_404(Account, account_id=account_id)
        tags = account.tag_set.all()
        data = []
        for tag in tags:
            data.append({'tag_id': tag.tag_id, 'name': tag.name})
        return Response(data, status=status.HTTP_200_OK)

class RetrieveUpdateDeleteTagView(RetrieveUpdateDestroyAPIView):
    pagination_class = [IsAuthenticated]
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    lookup_field = 'tag_id'


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
        quick_replies = QuickReply.objects.filter(account_id=account).select_related('account_id')
        serializer = QuickReplySerializer(quick_replies, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RetrieveUpdateDeleteQuickReplyView(RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = QuickReplySerializer
    lookup_field = 'quickreply_id'

    def get_queryset(self):
        account = self.kwargs['account_id']
        quick_reply_id = self.kwargs['quickreply_id']
        return QuickReply.objects.filter(account_id=account, quickreply_id=quick_reply_id).select_related('account_id')
    
    def perform_update(self, serializer):
        account_id = get_object_or_404(Account, account_id=self.kwargs['account_id'])
        serializer.save(account_id=account_id)
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        data = serializer.data
        
        # Convert image to base64 if exists
        if instance.image:
            try:
                with open(instance.image.path, 'rb') as image_file:
                    image_data = base64.b64encode(image_file.read()).decode('utf-8')
                    data['image_base64'] = image_data
                    data['image_content_type'] = 'image/jpeg' if instance.image.name.endswith('.jpg') or instance.image.name.endswith('.jpeg') else 'image/png'
            except Exception as e:
                data['image_base64'] = None
                data['image_error'] = str(e)
        else:
            data['image_base64'] = None
        
        return Response(data)


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
    
    def get_queryset(self):
        queryset = super().get_queryset()
        account_id = self.kwargs['account_id']
        tag = self.request.query_params.get('tag')
        
        # Filter by account
        queryset = queryset.filter(account_id=account_id)
        
        # If tag is provided, filter groups related to that tag
        if tag:
            # Get conversations with this tag
            conversations = Conversation.objects.filter(tags__tag_id=tag)
            # Get contacts from those conversations
            contact_ids = conversations.values_list('contact_id', flat=True).distinct()
            # Filter groups that contain any of these contacts
            queryset = queryset.filter(contact__in=contact_ids).distinct()
        
        return queryset
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['account_id'] = self.kwargs['account_id']
        
        # If creating with tag, get all contacts with that tag
        tag = self.request.query_params.get('tag')
        if tag and self.request.method == 'POST':
            # Get conversations with this tag
            conversations = Conversation.objects.filter(tags__tag_id=tag)
            # Get contacts from those conversations
            contact_ids = conversations.values_list('contact_id', flat=True).distinct()
            context['members'] = list(contact_ids)
        
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


class ListMessgesForSpecificConversation(GenericAPIView):
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPaginatins

    def get(self, request, conversation_id):
        paginator = CustomPaginatins()
        # paginator.page_size = 20
        conversation = Conversation.objects.get(conversation_id=conversation_id)
        messages = conversation.chatmessage_set.all().order_by('-created_at')
        result_page = paginator.paginate_queryset(messages, request)
        messages_serializer = ChatMessageSerializer(result_page, many=True)
        return paginator.get_paginated_response(messages_serializer.data)