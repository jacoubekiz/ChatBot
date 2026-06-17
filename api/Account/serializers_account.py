from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from api.Account.models_account import Account, Team, CustomUser


class AccontSerializer(serializers.ModelSerializer):
    channel_id = serializers.SerializerMethodField(read_only=True)
    email = serializers.SerializerMethodField(read_only=True)
    class Meta:
        model = Account
        fields = '__all__'

    def get_channel_id(self, obj):
        try:
            return obj.channle_set.all().first().channle_id
        except:
            return None
        
    def get_email(self, obj):
        try:
            return obj.user.email
        except:
            return None


class AddAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'password']
        extra_kwargs = {
            'password':{'write_only':True},
        }
        
    def validate(self, attrs):
        password = attrs.get('password')
        validate_password(password)
        return attrs
    
    def create(self, validated_data):
        password = self.validated_data.pop('password')
        user = CustomUser.objects.create(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UpdateAccountSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='username')

    class Meta:
        model = CustomUser
        fields = ['id', 'name', 'email']

    def update(self, instance, validated_data):
        user_id = self.context.get('user_id')
        
        if 'username' in validated_data:
            instance.username = validated_data['username']
        
        instance.email = validated_data.get('email', instance.email)
        instance.save()
        
        account = Account.objects.get(user_id=user_id)
        account.name = instance.username
        account.save()
        return instance


class MemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username']


class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ['team_id', 'account_id', 'name']
        extra_kwargs = {
            'account_id':{'read_only':True},
        }
    def create(self, validated_data):
        account_id = self.context.get('account_id')
        account = Account.objects.get(account_id=account_id)
        validated_data['account_id'] = account
        team = Team.objects.create(**validated_data)
        return team
    
    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        instance.save()
        return instance


class TeamMemberSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField(read_only=True)
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'username', 'phonenumber', 'role_user', 'role']

    def get_role(self, obj):
        roles = obj.user_permissions.all()
        return [role.codename for role in roles]
