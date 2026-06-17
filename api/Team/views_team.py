from rest_framework.generics import (
    GenericAPIView, 
    ListCreateAPIView, 
    RetrieveUpdateDestroyAPIView
)
from api.Account.serializers_account import (
    TeamSerializer, 
    TeamMemberSerializer, 
    MemberSerializer
)
from api.Auth.serializers_auth import AddUserSerializer, UpdateTeamMemberSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from rest_framework.views import APIView
from django.db.models import Q
from api.Account.models_account import Account, Team
from api.Auth.models_auth import CustomUser

class ListCreateTeamView(ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Team.objects.all()
    serializer_class = TeamSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['account_id'] = self.kwargs['account_id']
        return context
    
    def get_queryset(self):
        account_id = Account.objects.get(account_id=self.kwargs['account_id'])
        return account_id.team_set.all()


class RetrieveUpdateDeleteTeamView(RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TeamSerializer
    lookup_field = 'team_id'
    def get_queryset(self):
        account_id = self.kwargs['account_id']
        team_id = self.kwargs['team_id']
        return Team.objects.filter(account_id=account_id, team_id=team_id)
    
    def perform_update(self, serializer):
        account_id = Account.objects.get(account_id=self.kwargs['account_id'])
        serializer.save(account_id=account_id)


class AssigningPermissions(APIView):
    def post(self, request, user_id):
        user = CustomUser.objects.get(id=user_id)
        role = request.data['role']
        add = request.GET.get('add')
        content_type = ContentType.objects.get_for_model(CustomUser)
        permission = Permission.objects.get(
            codename=role,
            content_type=content_type
        )
        if add == 'True':
            user.user_permissions.add(permission)
        else:
            user.user_permissions.remove(permission)
        return Response(status=status.HTTP_200_OK)


class ListTeamMember(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TeamMemberSerializer
    def get(self, request, team_id):
        team = get_object_or_404(Team, team_id=team_id)
        members = team.members.all()
        serializer = self.serializer_class(members, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CreateTeamMemberView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, account_id):
        data_request = request.data
        serializer = AddUserSerializer(
            data=data_request, 
            many=False, 
            context={
                'role':request.data['role'], 
                'account_id': account_id
            }
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class AddUserForTeam(GenericAPIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, team_id):
        team = Team.objects.filter(team_id=team_id).first()
        if not team:
            return Response({'error':'Team not found'}, status=status.HTTP_200_OK)
        users = request.data['users']
        keword = request.GET.get('keword')
        for user in users:
            t_user = CustomUser.objects.filter(id=user).first()
            if not t_user:
                return Response({'error':'User not found'}, status=status.HTTP_200_OK)
            if keword == 'add':
                team.members.add(t_user)
            elif keword == 'delete':
                team.members.remove(t_user)
        return Response(status=status.HTTP_200_OK)


class RetrieveUpdateDeleteTeamMemberView(RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UpdateTeamMemberSerializer
    queryset = CustomUser.objects.all()
    lookup_field = 'pk'

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['role'] = self.request.data.get('role')
        return context
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        response_data = serializer.data
        user = get_object_or_404(CustomUser, email=response_data['email'])
        response_data['role'] = [perm.codename for perm in user.user_permissions.all()]
        return Response(response_data)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        response_data = serializer.data
        user = get_object_or_404(CustomUser, email=response_data['email'])
        response_data['role'] = [perm.codename for perm in user.user_permissions.all()]
        return Response(response_data)


class ListAllTeamMembers(GenericAPIView):

    permission_classes = [IsAuthenticated]
    def get(self, request, account_id):
        account = get_object_or_404(Account, account_id=account_id)
        member = CustomUser.objects.filter(Q(role_user="agent") & Q(manager=account.user))
        serializer = MemberSerializer(member, many=True)
        members = serializer.data
        return Response(members, status=status.HTTP_200_OK)
