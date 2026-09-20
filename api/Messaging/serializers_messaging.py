from tkinter.constants import TRUE
from rest_framework import serializers
from api.Flow.models_flow import Trigger
from api.Messaging.models_messaging import Group, QuickReply, Tag
from api.Account.models_account import Account
from api.Contact.models_contact import ChatMessage, Contact


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = '__all__'
        extra_kwargs = {
            'name': {
                'error_messages': {
                    'required': 'Tag name is required',
                    'blank': 'Tag name cannot be empty',
                    'max_length': 'Tag name cannot exceed 50 characters'
                }
            },
            
            'account_id': {
                'read_only': True
            }
        }

    def to_representation(self, instance):
        repr = super().to_representation(instance)
        repr['account_id'] = instance.account_id.name
        return repr


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ['message_id', 'user_id', 'from_message', 'content', 'caption', 'content_type', 'created_at', 'conversation_id', 'media_url', 'media_sha256_hash', 'status_message']
        extra_kwargs = {
            'user_id': {'read_only': True},
            'conversation_id': {
                'error_messages': {
                    'required': 'Conversation ID is required',
                    'invalid': 'Invalid conversation ID'
                }
            },
            'content_type': {
                'error_messages': {
                    'required': 'Content type is required',
                    'invalid_choice': 'Invalid content type'
                }
            },
            'wamid': {
                'error_messages': {
                    'required': 'WhatsApp message ID is required',
                    'max_length': 'WhatsApp message ID cannot exceed 500 characters'
                }
            },
            'content': {
                'error_messages': {
                    'max_length': 'Content cannot exceed 1000 characters'
                }
            },
            'caption': {
                'error_messages': {
                    'max_length': 'Caption cannot exceed 500 characters'
                }
            }
        }

    def to_representation(self, instance):
        repr = super().to_representation(instance)
        try:
            repr['user_id'] = instance.user_id.username
        except:
            pass
        return repr


class QuickReplySerializer(serializers.ModelSerializer):
    class Meta:
        model = QuickReply
        fields = '__all__'
        extra_kwargs = {
            'account_id': {'read_only': True},
            'name': {
                'error_messages': {
                    'required': 'Quick reply name is required',
                    'blank': 'Quick reply name cannot be empty',
                    'max_length': 'Quick reply name cannot exceed 100 characters'
                }
            },
            'payload': {
                'error_messages': {
                    'max_length': 'Payload cannot exceed 255 characters'
                }
            }
        }

    def create(self, validated_data):
        account_id = self.context.get('account_id')
        account = Account.objects.filter(account_id=account_id).first()
        if not account:
            raise serializers.ValidationError({'account_id': 'Account not found'})
        validated_data['account_id'] = account
        quick_reply = QuickReply.objects.create(**validated_data)
        return quick_reply

    def to_representation(self, instance):
        repr = super().to_representation(instance)
        repr['account_id'] = instance.account_id.name
        return repr


class TriggerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trigger
        fields = '__all__'
        extra_kwargs = {
            'account_id': {'read_only': True},
            'trigger': {
                'error_messages': {
                    'max_length': 'Trigger cannot exceed 50 characters'
                }
            }
        }

    def create(self, validated_data):
        account_id = self.context.get('account_id')
        account = Account.objects.filter(account_id=account_id).first()
        if not account:
            raise serializers.ValidationError({'account_id': 'Account not found'})
        validated_data['account'] = account
        trigger = Trigger.objects.create(**validated_data)
        return trigger

    def to_representation(self, instance):
        repr = super().to_representation(instance)
        repr['account'] = instance.account.name
        return repr


class GroupSerializer(serializers.ModelSerializer):
    tag_name = serializers.CharField(read_only=True)
    class Meta:
        model = Group
        fields = '__all__'
        extra_kwargs = {
            'account': {'read_only': True},
            'contact': {'read_only': True},
            'name': {
                'error_messages': {
                    'required': 'Group name is required',
                    'blank': 'Group name cannot be empty',
                    'max_length': 'Group name cannot exceed 50 characters'
                }
            }
        }

    def create(self, validated_data):
        account_id = self.context.get('account_id')
        members = self.context.get('members', [])
        tag_id = self.context.get('tag')
        account = Account.objects.filter(account_id=account_id).first()
        if not account:
            raise serializers.ValidationError({'account_id': 'Account not found'})
        validated_data['account'] = account
        
        # Handle tag assignment
        if tag_id:
            from api.Messaging.models_messaging import Tag
            try:
                tag = Tag.objects.get(tag_id=tag_id, account_id=account)
                validated_data['tag'] = tag
            except Tag.DoesNotExist:
                raise serializers.ValidationError({'tag': 'Tag not found or does not belong to this account'})
        
        group = Group.objects.create(**validated_data)
        for member in members:
            group.contact.add(member)
        return group

    def update(self, instance, validated_data):
        members = self.context.get('members', [])
        instance.name = validated_data.get('name', instance.name)
        
        # Handle tag update
        tag_data = self.context.get('tag')
        if tag_data is not None:
            if tag_data == '' or tag_data is None:
                instance.tag = None
            else:
                # Convert tag_data to integer if it's a string
                from api.Messaging.models_messaging import Tag
                try:
                    tag_id = int(tag_data) if isinstance(tag_data, str) else tag_data
                    tag = Tag.objects.get(tag_id=tag_id, account_id=instance.account)
                    instance.tag = tag
                except (ValueError, Tag.DoesNotExist):
                    raise serializers.ValidationError({'tag': 'Tag not found or does not belong to this account'})
        
        instance.contact.clear()
        instance.save()

        for member in members:
            instance.contact.add(member)
        return instance

    def to_representation(self, instance):
        repr = super().to_representation(instance)
        repr['contact'] = [con.name for con in instance.contact.all()]
        repr['tag_name'] = instance.tag.name
        if instance.tag:
            repr['tag'] = instance.tag.tag_id
        else:
            repr['tag'] = None
        return repr
