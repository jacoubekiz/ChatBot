# from rest_framework import serializers
# from django.contrib.auth import authenticate
# from rest_framework_simplejwt.tokens import RefreshToken
# from .models import *

# class AddUserSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Custom2User
#         fields  = ['username', 'email', 'password', 'role']

#     def set_token_for_user(self, obj):
#         email = self.validated_data.get('email')
#         user = Custom2User.objects.get(email=email)
#         token = RefreshToken.for_user(user)

#         tokens = {
#             'refresh':str(token), 
#             'access':str(token.access_token)
#         }
#         return tokens

# class LoginSerializer(serializers.Serializer):
#     username = serializers.CharField()
#     password = serializers.CharField(write_only = True)

#     def validate(self, data):
#         username = data.get('username')
#         password = data.get('password')

#         if username and password:
#             # print(username , password)
            
#             user = authenticate( username=username, password=password)
#             if not user:
#                 raise serializers.ValidationError("Incorrect Credentials")
#         else:
#             raise serializers.ValidationError('Must include "username" and "password".')

#         data['user'] = user
#         return data


# class TestWebhookSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = TestWebhook
#         fields = '__all__'

# from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
# from rest_framework_simplejwt.views import TokenObtainPairView

# class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
#     def validate(self, attrs):
#         data = super().validate(attrs)
#         refresh = self.get_token(self.user)
#         access = refresh.access_token
        
#         # Add user type to the token payload
#         access.payload['user_type'] = 'custom1' if isinstance(self.user, CustomUser) else 'custom2'
        
#         data['refresh'] = str(refresh)
#         data['access'] = str(access)
        
#         # Add extra fields here if needed
#         data['username'] = self.user.username
#         data['email'] = self.user.email
        
#         return data