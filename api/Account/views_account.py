from rest_framework.generics import GenericAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from api.Account.models_account import Account
from api.Auth.models_auth import CustomUser
from api.handel_templates.models_template import TemplateBox
from api.Account.serializers_account import (
    AddAccountSerializer, 
    UpdateAccountSerializer, 
    AccontSerializer
)


class CreateListAccount(GenericAPIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        data_request = request.data
        serializer = AddAccountSerializer(data=data_request, many=False)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        email = data_request['email']
        user = get_object_or_404(CustomUser, email=email)
        account = Account.objects.create(
            user=user,
            name=user.username
        )
        template_box, _ = TemplateBox.objects.get_or_create(account=account, box_name=f'box for accont{account.name}')
        return Response(status=status.HTTP_201_CREATED)

    def get(self, request):
        accounts = Account.objects.filter(user__role_user='admin').select_related('user')
        if not accounts:
            return Response({'error':'Dont have permission for this action'}, status=status.HTTP_200_OK)
        serializer = AccontSerializer(accounts, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RetrieveUpdateDeleteAccount(RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UpdateAccountSerializer
    queryset = CustomUser.objects.all()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['user_id'] = self.kwargs.get('pk')
        return context


class GenerateapiKeyView(GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, account_id):
        account = get_object_or_404(Account, account_id=account_id)
        account.apiKey = account.generate_key()
        account.save()
        message = {
            "account": account.name,
            "apiKey": account.apiKey
        }

        return Response(message, status=status.HTTP_200_OK)

    def get(self, request, account_id):
        account = get_object_or_404(Account, account_id=account_id)
        message = {
            "apikey": account.apiKey
        }
        return Response(message, status=status.HTTP_200_OK)
