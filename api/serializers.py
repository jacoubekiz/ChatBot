from rest_framework import serializers
from django.contrib.auth import  authenticate
from django.contrib.auth.password_validation import validate_password
from django.utils.duration import duration_string
from .models import *

class ClientSerializer(serializers.ModelSerializer):
    
    class Meta:

        model = Client
        fields = '__all__'


class SerializerSignUp(serializers.ModelSerializer):

    class Meta:
        model = CustomUser
        fields = ['email', 'phonenumber', 'username', 'password']
        extra_kwargs = {
            'password':{'write_only':True},
        }
        
        def validate(self, attrs):
            password = attrs.get('password')
            validate_password(password)
            return attrs
    
        
class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only = True)

    def validate(self, data):
        username = data.get('username')
        password = data.get('password')
        print(username + ' ' + password)
        user = authenticate(request=self.context.get('request'), username=username, password=password)
        if not user:
            raise serializers.ValidationError({"error":"لا يوجد مستخدم بهذه المعلومات"})
        if not user.is_active:
            raise serializers.ValidationError({"error":"هذا الحساب غير مفعل"})

        data['user'] = user
        return data


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