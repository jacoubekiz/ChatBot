from rest_framework import serializers
from api.Flow.models_flow import Trigger
from api.Messaging.models_messaging import Group, QuickReply, Tag
from api.Account.models_account import Account


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = '__all__'


class QuickReplySerializer(serializers.ModelSerializer):
    class Meta:
        model = QuickReply
        fields = '__all__'
        extra_kwargs = {
            'account_id':{'read_only':True},
        }

    def create(self, validated_data):
        account_id = self.context.get('account_id')
        account = Account.objects.filter(account_id=account_id).first()
        validated_data['account_id'] = account
        quick_reply = QuickReply.objects.create(**validated_data)
        return quick_reply
    
    def to_representation(self, instance):
        repre = super().to_representation(instance)
        repre['account_id'] = instance.account_id.name
        return repre


class TriggerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trigger
        fields = '__all__'
        extra_kwargs = {
            'account_id':{'read_only':True},
        }

    def create(self, validated_data):
        account_id = self.context.get('account_id')
        account = Account.objects.filter(account_id=account_id).first()
        validated_data['account'] = account
        trigger = Trigger.objects.create(**validated_data)
        return trigger
    
    def to_representation(self, instance):
        repre = super().to_representation(instance)
        repre['account'] = instance.account.name
        return repre


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = '__all__'
        extra_kwargs = {
            'account':{'read_only':True},
            'contact':{'read_only':True},
        }

    def create(self, validated_data):
        account_id = self.context.get('account_id')
        members = self.context.get('members', [])
        account = Account.objects.filter(account_id=account_id).first()
        validated_data['account'] = account
        group = Group.objects.create(**validated_data)
        for member in members:
            group.contact.add(member)
        return group

    def update(self, instance, validated_data):
        members = self.context.get('members', [])
        instance.name = validated_data.get('name', instance.name)
        instance.contact.clear()
        instance.save()

        for member in members:
            instance.contact.add(member)
        return instance
