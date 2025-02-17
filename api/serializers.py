from rest_framework import serializers
from django.contrib.auth import  authenticate
from django.contrib.auth.password_validation import validate_password
from django.utils.duration import duration_string
from .models import *

class ClientSerializer(serializers.ModelSerializer):
    
    class Meta:

        model = Client
        fields = '__all__'


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
        model = CustomUser1
        fields  = ['id', 'username', 'email', 'password', 'role']
        extra_kwargs = {
            'password':{'write_only':True},
        }
        
    def validate(self, attrs):
        password = attrs.get('password')
        validate_password(password)
        return attrs
    
    def create(self, validated_data):
        request = self.context.get('request')
        user_ = CustomUser1.objects.get(id=request.user.id)
        validated_data['account_id'] = user_.account_id
        password = self.validated_data.pop('password')
        user = CustomUser1.objects.create(**validated_data)
        user.set_password(password)
        user.save()
        return user
    
    
        
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


class TeamAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fiedls = ['account_id', 'name']

class TeamSerializer(serializers.ModelSerializer):
    members = TeamAccountSerializer(read_only=True, many=True)

    class Meta:
        model = Team
        fields = ['id', 'name', 'members']

class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ['contact_id', 'name', 'phone_number']

class ConversationContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ['name', 'phone_number']


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ['message_id', 'from_message', 'content','caption', 'content_type', 'created_at', 'conversation_id', 'media_url', 'media_sha256_hash']

class ConversationSerializer(serializers.ModelSerializer):
    contact_id = ConversationContactSerializer(read_only=True)
    last_message = serializers.SerializerMethodField(read_only=True)
    # last_message = ChatMessageSerializer(read_only=True)
    
    class Meta:
        model = Conversation
        fields = ['conversation_id', 'contact_id', 'status', 'last_message']

    def get_last_message(self, obj):
            last_message = obj.chatmessage_set.order_by('-created_at').first()
            return ChatMessageSerializer(last_message).data if last_message else None

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

class CampaignsSerilizer(serializers.ModelSerializer):
    class Meta:
        model = Campaign
        fields = ['campaign_id', 'name', 'status', 'start_date', 'end_date']

        extra_kwargs = {
            'status':{'read_only':True},
            'start_date':{'write_only': True},
            'end_date': {'write_only': True}
        }


class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = ['report_id', 'name', 'data']

    