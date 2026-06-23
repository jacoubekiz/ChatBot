from django.shortcuts import get_object_or_404
from rest_framework import serializers
from api.Contact.models_contact import Contact, Conversation, ChatMessage
from api.Messaging.models_messaging import Tag
from api.Channel.models_channel import Channle

class ConversationContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ['contact_id', 'name', 'phone_number']


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ['message_id', 'user_id', 'from_message', 'content', 'caption', 'content_type', 'created_at', 'conversation_id', 'media_url', 'media_sha256_hash', 'status_message']

        extra_kwargs = {
            'user_id':{'read_only': True},
        }

    def to_representation(self, instance):
        repr = super().to_representation(instance)
        try:
            repr['user_id'] = instance.user_id.username
            return repr
        except:
            return repr


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = '__all__'


class TagConversationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['tag_id', 'name']


class ConversationSerializer(serializers.ModelSerializer):
    contact_id = ConversationContactSerializer(read_only=True)
    last_message = serializers.SerializerMethodField(read_only=True)
    timer = serializers.SerializerMethodField(read_only=True)
    tags = serializers.SerializerMethodField(read_only=True)
    channel_id = serializers.CharField(source='channle_id.channle_id', read_only=True)
    channel_name = serializers.CharField(source='channle_id.name', read_only=True)

    class Meta:
        model = Conversation
        fields = ['conversation_id', 'contact_id', 'status', 'state', 'last_message', 'user', 'timer', 'tags', 'channel_id', 'channel_name']

    def get_last_message(self, obj):
        last_message = obj.chatmessage_set.order_by('-created_at').first()
        return ChatMessageSerializer(last_message).data if last_message else None
    
    def get_timer(self, obj):
        timer = obj.chatmessage_set.exclude(from_message='bot').order_by('-created_at').first()
        return ChatMessageSerializer(timer).data["created_at"] if timer else None
    
    def get_tags(self, obj):
        tags = obj.tags.all()
        return TagConversationSerializer(tags, many=True).data


class ConverstionSerializerCreate(serializers.ModelSerializer):
    class Meta:
        model = Conversation
        fields = ['conversation_id', 'contact_id', 'channle_id', 'status']

        extra_kwargs = {
            'status':{'read_only': True},
            'conversation_id':{'read_only': True},
            'contact_id':{'write_only':True},
            'channle_id':{'write_only':True}
        }


class ContactSerializerView(serializers.ModelSerializer):
    conversation_id = serializers.SerializerMethodField(read_only=True)
    assigned_user = serializers.SerializerMethodField(read_only=True)
    tags = serializers.SerializerMethodField()

    class Meta:
        model = Contact
        fields = ['contact_id', 'account_id', 'name', 'assigned_user', 'phone_number', 'email', 'conversation_id', 'tags']
        extra_kwargs ={
            'account_id':{
                'required':False,
                'allow_null':False
            },
            'conversation_id':{
                'required':False,
                'allow_null':False
            }
        }

    def get_assigned_user(self, obj):
        try:
            conversation = Conversation.objects.filter(contact_id=obj.contact_id).first()
            return conversation.user.username if conversation.user else None
        except Conversation.DoesNotExist:
            return None
        
    def get_conversation_id(self, obj):
        conversation = Conversation.objects.filter(contact_id=obj.contact_id)
        return [{
            "conversation_id": conv.conversation_id, 
            "channel_id": conv.channle_id.channle_id,
            "channel_name": conv.channle_id.name
            } 
            for conv in conversation] if conversation else None

    def to_representation(self, instance):
        repre = super().to_representation(instance)
        repre['account_id'] = instance.account_id.name
        return repre
    
    def get_tags(self, obj):
        tags = Tag.objects.filter(
            conversation__contact_id=obj
        ).distinct().values('tag_id', 'name')
        return list(tags)


class ContactSerializer(serializers.ModelSerializer):
    conversation_id = serializers.SerializerMethodField(read_only=True)
    assigned_user = serializers.SerializerMethodField(read_only=True)
    tags = serializers.SerializerMethodField()

    class Meta:
        model = Contact
        fields = ['contact_id', 'account_id', 'name', 'assigned_user', 'phone_number', 'email', 'conversation_id', 'tags']
        extra_kwargs ={
            'account_id':{
                'required':False,
                'allow_null':False
            },
            'conversation_id':{
                'required':False,
                'allow_null':False
            }
        }

    def get_assigned_user(self, obj):
        try:
            conversation = Conversation.objects.filter(contact_id=obj.contact_id).first()
            return conversation.user.username if conversation.user else None
        except Conversation.DoesNotExist:
            return None
    
    def update(self, instance, validated_data):
        instance.account_id = validated_data.get('account_id', instance.account_id)
        instance.name = validated_data.get('name', instance.name)
        instance.phone_number = validated_data.get('phone_number', instance.phone_number)
        instance.email = validated_data.get('email', instance.email)
        instance.save()
        return instance
    
    def get_conversation_id(self, obj):
        channel_id = Channle.objects.get(channle_id=self.context.get('channel_id'))
        account_id = channel_id.account_id
        contact = Contact.objects.get(contact_id=obj.contact_id)
        conversation_id = Conversation.objects.get_or_create(contact_id=contact, channle_id=channel_id, account_id=account_id)[0]
        return conversation_id.conversation_id if conversation_id else None

    def to_representation(self, instance):
        channel = get_object_or_404(Channle, channle_id= self.context.get('channel_id'))
        repre = super().to_representation(instance)
        repre['channel_name'] = channel.name
        repre['account_id'] = instance.account_id.name
        return repre
    
    def get_tags(self, obj):
        tags = Tag.objects.filter(
            conversation__contact_id=obj
        ).distinct().values('tag_id', 'name')
        return list(tags)


class ConvSerializer(serializers.ModelSerializer):
    channel = serializers.CharField(source='channle_id.name', read_only=True)
    assigned_user = serializers.CharField(source='user.username', read_only=True)
    class Meta:
        model = Conversation
        fields = ['conversation_id', 'channle_id', 'tags', 'status', 'assigned_user', 'channel']

    def to_representation(self, instance):
        repr = super().to_representation(instance)
        repr['tags'] = [{"tag_id":tag.tag_id, "name":tag.name} for tag in instance.tags.all()]
        return repr
