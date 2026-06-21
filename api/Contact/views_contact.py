from rest_framework.generics import (
    GenericAPIView, 
    RetrieveUpdateDestroyAPIView, 
    DestroyAPIView, 
    ListAPIView
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from api.Auth.models_auth import CustomUser
from api.Channel.models_channel import Channle
from api.Contact.models_contact import Contact, Conversation
from api.Account.models_account import Account
from api.Messaging.models_messaging import Tag
from api.Flow.models_flow import Chat
from api.Contact.serializers_contact import (
    ContactSerializer, 
    ContactSerializerView, 
    ConversationSerializer, 
    ConverstionSerializerCreate
)
from api.Core.filters import ContactFilter
from django_filters.rest_framework import DjangoFilterBackend


class CreateNewContact(GenericAPIView):
    def post(self, request, account_id, channel_id):
        data = request.data
        account = get_object_or_404(Account, account_id=account_id)
        channel = get_object_or_404(Channle, channle_id=channel_id)
        contact, created = Contact.objects.get_or_create(
            phone_number=data['phone_number'], 
            account_id=account
        )
        contact.name = request.data['name']
        contact.save()
        if created:
            conversation = Conversation.objects.create(
                contact_id=contact, 
                channle_id=channel, 
                account_id=account
                )
            serializer = ContactSerializer(contact, context={'channel_id': channel.channle_id, 'account_id': account.account_id})
            data = serializer.data
            return Response(data, status=status.HTTP_200_OK)
        else:
            serializer = ContactSerializer(contact, context={'channel_id': channel.channle_id, 'account_id': account.account_id})
            data = serializer.data
            return Response(data, status=status.HTTP_302_FOUND)


class RetrieveUpdateDestroyContactView(RetrieveUpdateDestroyAPIView):
    serializer_class = ContactSerializer
    permission_classes = [IsAuthenticated]
    queryset = Contact.objects.all()
    lookup_field = 'contact_id'

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['channel_id'] = self.kwargs['channel_id']
        return context

    def perform_destroy(self, instance):
        """Delete Chat records where conversation_id equals contact phone number."""
        # Delete Chat records where conversation_id equals the contact's phone number
        Chat.objects.filter(conversation_id=instance.phone_number).delete()
        # Call the parent's perform_destroy to delete the contact
        super().perform_destroy(instance)


class ListContactView(ListAPIView):
    queryset = Contact.objects.all().prefetch_related(
        'conversation_set__tags'
    )
    serializer_class = ContactSerializerView
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = ContactFilter


class ListConversationView(GenericAPIView):
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request, channel_id):
        user = get_object_or_404(CustomUser, id=request.user.id)
        permissions = list(user.get_all_permissions())
        if 'api.visibility all conversations' in permissions:
            conversation = Conversation.objects.filter(channle_id=channel_id).select_related('contact_id', 'channle_id', 'account_id')
            if not conversation:
                return Response({'error':'No conversations found'}, status=status.HTTP_200_OK)
            serializer = self.get_serializer(conversation, many=True, context={'user':request.user})
            return Response(serializer.data)
        else:
            conversation = Conversation.objects.filter(channle_id=channel_id, user=user).select_related('contact_id', 'channle_id', 'account_id')
            if not conversation:
                return Response({'error':'No conversations found'}, status=status.HTTP_200_OK)
            serializer = self.get_serializer(conversation, many=True, context={'user':request.user})
            return Response(serializer.data)
    
    def post(self, request, channel_id):
        channel = get_object_or_404(Channle.objects.select_related('account_id', 'contact_id'), channle_id=channel_id)
        contact = get_object_or_404(Contact.objects.select_related('account_id'), contact_id=channel.contact_id.contact_id)
        conversation, created = Conversation.objects.get_or_create(contact_id=contact, channle_id=channel)
        conversation_serializer = ConverstionSerializerCreate(conversation, many=False)
        return Response(conversation_serializer.data)


class DeleteConversation(DestroyAPIView):
    queryset = Conversation.objects.all()
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'conversation_id'


class ReasignConversation(GenericAPIView):
    def post(self, request, conversation_id):
        data = request.data
        conversation = get_object_or_404(Conversation, conversation_id=conversation_id)
        user = get_object_or_404(CustomUser, id=data['user_id'])
        conversation.user = user
        conversation.save()

        return Response(status=status.HTTP_200_OK)


class InitiateLiveChat(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, conversation_id):
        state = request.data['state']
        conversation = get_object_or_404(Conversation, conversation_id=conversation_id)
        conversation.state = state
        conversation.save()
        return Response(status=status.HTTP_200_OK)


class ChangeConversationStatus(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, conversation_id):
        status_ = request.data['status']
        conversation = get_object_or_404(Conversation, conversation_id=conversation_id)
        conversation.status = status_
        conversation.save()
        return Response(status=status.HTTP_200_OK)


class AddTagToConversation(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, conversation_id):
        tag_ids = request.data.get('tag_ids', [])
        conversation = get_object_or_404(Conversation, conversation_id=conversation_id)
        for tag_id in tag_ids:
            tag = Tag.objects.filter(tag_id=tag_id).first()
            if not tag:
                return Response({"error":f"tag with {tag_id} not found"}, status=status.HTTP_204_NO_CONTENT)
            conversation.tags.add(tag)
        conversation.save()
        return Response(status=status.HTTP_200_OK)


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
