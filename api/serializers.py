from rest_framework import serializers
from django.contrib.auth import  authenticate
from django.contrib.auth.password_validation import validate_password
from django.utils.duration import duration_string
from .models import *
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

# class ClientSerializer(serializers.ModelSerializer):
    
#     class Meta:

#         model = Client
#         fields = '__all__'


# class SerializerSignUp(serializers.ModelSerializer):



class DurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Duration
        fields =   ['duration']

# class WorkingHoursAMSerializer(serializers.ModelSerializer):

#     class Meta:
#         model = WorkingHoursAM
#         fields = ['day', 'starting_time', 'expire_time']

    # def to_representation(self, instance):
    #     repr = super().to_representation(instance)
    #     days = ['الأحد', 'الإثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت']
    #     repr['day'] = days[int(instance.day) - 1]
    #     return repr

# class WorkingHoursPMSerializer(serializers.ModelSerializer):

#     class Meta:
#         model = WorkingHoursPM
#         fields = ['day', 'starting_time', 'expire_time']

#     def to_representation(self, instance):
#         repr = super().to_representation(instance)
#         days = ['الأحد', 'الإثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت']
#         repr['day'] = days[int(instance.day) - 1]
#         return repr

class WorkingTimeSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkingTime
        fields = '__all__'

        extra_kwargs = {
            'user':{'read_only':True}
        }

    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['user'] = request.user
        working_time = WorkingTime.objects.create(**validated_data)
        return working_time
    
    def to_representation(self, instance):
        repr = super().to_representation(instance)
        days = ['الأحد', 'الإثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت']
        repr['day'] = days[int(instance.day) - 1]
        repr['user'] = instance.user.username
        return repr

class CalenderSerializer(serializers.ModelSerializer):
    working_time = WorkingTimeSerializer(many=True, read_only=True)

    class Meta:
        model = Calendar
        fields = '__all__'

        extra_kwargs = {
            'user':{'read_only':True},
            'key':{'read_only':True}
        }
    
    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['user'] = request.user
        calender = Calendar.objects.create(**validated_data)
        working_time = WorkingTime.objects.filter(user=request.user).all()
        for work_time in working_time :
            calender.working_time.add(work_time)
            calender.save()
        return calender
    

    def to_representation(self, instance):
        repr = super().to_representation(instance)
        repr['user'] = instance.user.username
        return repr
    
    
class BookAnAppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookAnAppointment
        fields = '__all__'







# ---------------------------------------------------------------------------------------------------------
from rest_framework_simplejwt.tokens import RefreshToken, TokenError

class AddUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields  = ['id', 'username', 'phonenumber', 'email', 'password', 'role_user']
        extra_kwargs = {
            'password':{
                'write_only':True,
                'required':False,
                'allow_null':False
            },
        }
        
    def validate(self, attrs):
        password = attrs.get('password')
        validate_password(password)
        return attrs
    
    def create(self, validated_data):
        # request = self.context.get('request')
        roles = self.context.get('role')
        # team = Team.objects.get(team_id = self.context.get('team_id', ' '))
        password = self.validated_data.pop('password')
        user = CustomUser.objects.create(**validated_data)
        for role in roles:
            content_type = ContentType.objects.get_for_model(CustomUser)
            permission = Permission.objects.get(
                codename= role,
                content_type=content_type
            )
            user.user_permissions.add(permission)
        user.set_password(password)
        user.save()
        # team.members.add(user)
        return user
    
    def update(self, instance, validated_data):
        instance.username = validated_data.get('username', instance.username)
        instance.email = validated_data.get('email', instance.email)
        instance.phonenumber = validated_data.get('phonenumber', instance.phonenumber)
        instance.role_user = validated_data.get('role_user', instance.role_user)
        instance.save()
        roles = self.context.get('role')
        instance.user_permissions.clear()
        user = CustomUser.objects.get(email=instance.email)
        for role in roles:
            content_type = ContentType.objects.get_for_model(CustomUser)
            permission = Permission.objects.get(
                codename= role,
                content_type=content_type
            )
            user.user_permissions.add(permission)
        return instance
    
class AccontSerializer(serializers.ModelSerializer):
    channel_id = serializers.SerializerMethodField(read_only=True)
    email = serializers.SerializerMethodField(read_only=True)
    class Meta:
        model = Account
        fields = '__all__'
        # fields = ['account_id', 'name', 'user', 'channel_id']

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
        fields  = ['id', 'username', 'email', 'password']
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
    name = serializers.CharField(source='username')  # Map 'name' to 'username' field

    class Meta:
        model = CustomUser
        fields = ['id', 'name', 'email']  # Use 'name' instead of 'username'

    def update(self, instance, validated_data):
        user_id = self.context.get('user_id')
        
        # Handle the username update (coming from 'name' field)
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

class LoginSerializer(serializers.Serializer):
    email = serializers.CharField()
    password = serializers.CharField(write_only = True)

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')
        print(email, password)
        user = authenticate(request=self.context.get('request'), username=email, password=password)
        if not user:
            raise serializers.ValidationError({"error":"لا يوجد مستخدم بهذه المعلومات"})
        if not user.is_active:
            raise serializers.ValidationError({"error":"هذا الحساب غير مفعل"})

        data['user'] = user
        return data
    
class LogoutSerializer(serializers.Serializer):

    refresh = serializers.CharField()
    def validate(self, attrs):
        self.token = attrs['refresh']
        return attrs
    def save(self, **kwargs):
        try:
            RefreshToken(self.token).blacklist()
        except TokenError:
            self.fail('bad_token')


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'phonenumber', 'role_user']
# class TeamAccountSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Account
#         fiedls = ['account_id', 'name']

class TeamSerializer(serializers.ModelSerializer):
    # members = TeamAccountSerializer(read_only=True, many=True)

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

class ChannleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Channle
        # fields = ['channle_id', 'account_id', 'type_channle', 'tocken', 'phone_number']
        fields = '__all__'
        extra_kwargs = {
            'account_id':{'read_only':True},
        }

        def update(self, instance, validated_data):
            instance.type_channle = validated_data.get('type_channle', instance.type_channle)
            instance.tocken = validated_data.get('tocken', instance.tocken)
            instance.phone_number = validated_data.get('phone_number', instance.phone_number)
            instance.phone_number_id = validated_data.get('phone_number_id', instance.phone_number_id)
            instance.organization_id = validated_data.get('organization_id', instance.organization_id)
            instance.name = validated_data.get('name', instance.name)
            instance.save()
            return instance

class ContactSerializer(serializers.ModelSerializer):
    conversation_id = serializers.SerializerMethodField(read_only=True)
    assigned_user = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Contact
        fields = ['contact_id', 'assigned_user',     'account_id', 'name', 'phone_number', 'email', "conversation_id"]
        extra_kwargs ={
            'account_id':{
                # 'read_only':True,
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
            conversation = Conversation.objects.get(contact_id=obj.contact_id)
            return conversation.user.username if conversation.user else None
        except Conversation.DoesNotExist:
            return None
        
    def create(self, validated_data):
        account_id = self.context.get('account_id')
        channel_id = self.context.get('channel_id')
        validated_data['account_id'] = account_id
        contact = Contact.objects.create(**validated_data)
        conversation = Conversation.objects.create(account_id=account_id, channle_id=channel_id, contact_id=contact)
        return contact
    
    def update(self, instance, validated_data):
        instance.account_id = validated_data.get('account_id', instance.account_id)
        instance.name = validated_data.get('name', instance.name)
        instance.phone_number = validated_data.get('phone_number', instance.phone_number)
        instance.email = validated_data.get('email', instance.email)
        instance.save()
        return instance
    
    def get_conversation_id(self, obj):
        contact = Contact.objects.get(contact_id=obj.contact_id)
        conversation_id = Conversation.objects.get(contact_id=contact.contact_id)
        conversation_id = conversation_id.conversation_id
        return conversation_id
    
    def to_representation(self, instance):
        repre = super().to_representation(instance)
        repre['account_id'] = instance.account_id.name
        # repre['contact_id'] = instance.contact_id.name
        return repre
    
class ConversationContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ['contact_id', 'name', 'phone_number']


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ['message_id', 'user_id', 'from_message', 'content','caption', 'content_type', 'created_at', 'conversation_id', 'media_url', 'media_sha256_hash', 'status_message']

        extra_kwargs = {
            'user_id':{'read_only': True},
        }

    def to_representation(self, instance):
        repr =  super().to_representation(instance)
        try :
            repr['user_id'] = instance.user_id.username
            return repr
        except:
            return repr
        
class ConversationSerializer(serializers.ModelSerializer):
    contact_id = ConversationContactSerializer(read_only=True)
    last_message = serializers.SerializerMethodField(read_only=True)
    timer = serializers.SerializerMethodField(read_only=True)

    
    
    class Meta:
        model = Conversation
        fields = ['conversation_id', 'contact_id', 'status', 'state', 'last_message', 'user', 'timer']

    def get_last_message(self, obj):
            last_message = obj.chatmessage_set.order_by('-created_at').first()
            return ChatMessageSerializer(last_message).data if last_message else None
    
    def get_timer(self, obj):
        timer = obj.chatmessage_set.exclude(from_message='bot').order_by('-created_at').first()
        return ChatMessageSerializer(timer).data["created_at"] if timer else None


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

class AnalyticsCampaignSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalyticsCampaign
        fields = '__all__'

    def to_representation(self, instance):
        repre = super().to_representation(instance)
        repre['account_id'] = instance.account_id.name
        repre['campaign_id'] = instance.campaign_id.name
        repre['contact'] = instance.contact.name
        return repre
    
class CampaignsSerilizer(serializers.ModelSerializer):
    analytics_campaign = AnalyticsCampaignSerializer(many=True, read_only=True, source='analyticscampaign_set')
    class Meta:
        model = WhatsAppCampaign
        fields = ['campaign_id', 'name', 'status', 'analytics_campaign']

        extra_kwargs = {
            'status':{'read_only':True},
            # 'start_date':{'write_only': True},
            # 'end_date': {'write_only': True}
        }


class TeamMemberSerializer(serializers.ModelSerializer):
    permission = serializers.SerializerMethodField(read_only=True)
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'username', 'phonenumber', 'role_user', 'permission']

    def get_permission(self, obj):
        permissions = obj.user_permissions.all()
        return [perm.codename for perm in permissions]
    
class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = ['report_id', 'name', 'data']


class SerializerFlows(serializers.ModelSerializer):
    class Meta:
        model = Flow
        fields = '__all__'

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = '__all__'

class ChangePasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(required=True)
    confirm_password = serializers.CharField(required=True)

    def validate(self, attrs):
        new_password = attrs.get('new_password')
        confirm_password = attrs.get('confirm_password')
        if new_password != confirm_password:
            raise serializers.ValidationError("كلمات المرور غير متطابقة.")
        validate_password(new_password)
        return attrs
    
    def save(self, **kwargs):
        user = self.context.get('user')
        # user_login = CustomUser.objects.get(id=)
        if self.context.get('user_login').role_user != 'admin':
            raise serializers.ValidationError("ليس لديك الصلاحية للقيام بهذا الإجراء")
        new_password = self.validated_data.get('new_password')
        user.set_password(new_password)
        user.save()
        return user
    

class APISerializer(serializers.ModelSerializer):
    class Meta:
        model = API
        fields = ['api_id', 'api_name', 'endpoint', 'method', 'body']

    def create(self, validated_data):
        parameters = self.context.get('parameters', [])
        account = self.context.get('account')
        validated_data['account_id'] = account
        api = API.objects.create(**validated_data)
        if parameters:
            for param in parameters:
                for key, value in param.items():
                    param_obj = Parameter.objects.create(
                        account_id=account,
                        api = api,
                        key=key,
                        value=value
                    )
        return api

class ParameterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parameter
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
    