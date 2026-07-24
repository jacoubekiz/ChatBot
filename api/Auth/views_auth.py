from rest_framework.views import APIView
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import get_object_or_404
from api.Auth.models_auth import CustomUser
from api.Account.models_account import Team, Account
from api.Channel.models_channel import Channle
from api.handel_templates.models_template import TemplateBox
from api.Auth.serializers_auth import (
    LoginSerializer, 
    LogoutSerializer, 
    ChangePasswordSerializer
)


class RefreshTokenView(GenericAPIView):
    def post(self, request):
        refresh_token = request.data['refresh']
        token = RefreshToken(refresh_token)
        data = {
            'access': str(token.access_token)
        }
        return Response(data, status=status.HTTP_200_OK)


class ViewLogin(GenericAPIView):

    def post(self, request):
        data_request = request.data
        serializer = LoginSerializer(data=data_request, many=False)
        serializer.is_valid(raise_exception=True)
        email = data_request['email']
        try:
            user = get_object_or_404(CustomUser, email=email)
            token = RefreshToken.for_user(user)
            tokens = {'refresh':str(token), 'access':str(token.access_token)}
            team = Team.objects.filter(members__id=user.id).first()
            account_id = team.account_id.account_id
            channel_id = Channle.objects.filter(account_id__account_id=account_id).first()
            if user.role_user == 'admin':
                data = {
                    'tokens':tokens,
                    'user': {
                        'id':user.id,
                        'name':user.username,
                        'role':user.role_user,
                        'account_id': account_id,
                        'channel_id': channel_id.channle_id,
                        'permissions': [perm.split('.')[1] for perm in user.get_all_permissions()]
                    }
                }
            else:
                data = {
                    'tokens':tokens,
                    'user': {
                        'id':user.id,
                        'name':user.username,
                        'permissions':[perm.split('.')[1] for perm in user.get_all_permissions()],
                        'account': {
                            "account_id":account_id,
                            "name": team.account_id.name,
                            "email": team.account_id.user.email,
                            "channel_id":channel_id.channle_id
                        }
                    }
                }
        except:
            user = get_object_or_404(CustomUser, email=email)
            token = RefreshToken.for_user(user)
            team = Team.objects.filter(members__id=user.id).first()
            account_id = team.account_id.account_id if team else None
            tokens = {'refresh':str(token), 'access':str(token.access_token)}
            data = {
                'tokens':tokens,
                'user': {
                    'id':user.id,
                    'account_id': account_id,
                    'name':user.username,
                    'permissions':[perm.split('.')[1] for perm in user.get_all_permissions()],
                }
            }
        return Response(data, status=status.HTTP_200_OK)


class LogoutAPIView(APIView):
    serializer_class = LogoutSerializer
    permission_classes = [IsAuthenticated,]

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": 'logout true'})


class ChangePasswordView(GenericAPIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, user_id):
        data = request.data
        user = get_object_or_404(CustomUser, id=user_id)
        serializer = ChangePasswordSerializer(data=data, context={'user': user, 'user_login': request.user})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'message': 'Password changed successfully.'}, status=status.HTTP_200_OK)
