from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from django.contrib.auth.models import Permission
from django.contrib.auth import authenticate
from django.contrib.contenttypes.models import ContentType
from api.Auth.models_auth import CustomUser, Duration, WorkingTime, Calendar, BookAnAppointment


class DurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Duration
        fields = ['duration']


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


class UpdateTeamMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'phonenumber', 'email', 'role_user', 'manager']
        extra_kwargs = {
            'manager':{
                'read_only':True,
                'required': False
            }
        }

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

    def to_representation(self, instance):
        repre = super().to_representation(instance)
        repre['manager'] = instance.manager.username if instance.manager else None
        return repre


class AddUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'phonenumber', 'email', 'password', 'role_user', 'manager']
        extra_kwargs = {
            'password':{
                'write_only':True,
                'required':False,
                'allow_null':False
            },
            'manager':{
                'read_only':True,
                'required': False
            }
        }
        
    def validate(self, attrs):
        password = attrs.get('password')
        validate_password(password)
        return attrs
    
    def create(self, validated_data):
        from api.models import Account
        manager = self.context.get('account_id')
        manager_ = Account.objects.get(account_id=manager)
        roles = self.context.get('role')
        password = self.validated_data.pop('password')
        validated_data['manager'] = manager_.user
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

    def to_representation(self, instance):
        repre = super().to_representation(instance)
        repre['manager'] = instance.manager.username if instance.manager else None
        return repre


class LoginSerializer(serializers.Serializer):
    email = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')
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
        if self.context.get('user_login').role_user != 'admin':
            raise serializers.ValidationError("ليس لديك الصلاحية للقيام بهذا الإجراء")
        new_password = self.validated_data.get('new_password')
        user.set_password(new_password)
        user.save()
        return user
