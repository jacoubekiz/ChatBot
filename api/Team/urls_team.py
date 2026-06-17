from django.urls import path
from .views_team import (
    ListCreateTeamView,
    RetrieveUpdateDeleteTeamView,
    CreateTeamMemberView,
    AddUserForTeam,
    ListTeamMember,
    RetrieveUpdateDeleteTeamMemberView,
    ListAllTeamMembers,
    AssigningPermissions
)

urlpatterns = [
    path('assign-role/<user_id>/', AssigningPermissions.as_view(), name='assign_role'),
    path('add-team/<account_id>/', ListCreateTeamView.as_view(), name='teams'),
    path('update-delete-team/<str:team_id>/<str:account_id>/', RetrieveUpdateDeleteTeamView.as_view(), name='update_delete_team'),
    path('add-team-member/<str:account_id>/', CreateTeamMemberView.as_view(), name='users'),
    path('assign-user-for-team/<str:team_id>/', AddUserForTeam.as_view(), name="add_user_for_team"),
    path('list-team-member/<str:team_id>/', ListTeamMember.as_view(), name='team_members'),
    path('update-delete-team-member/<str:pk>/', RetrieveUpdateDeleteTeamMemberView.as_view(), name='update_delete_team_member'),
    path('list-all-members/<str:account_id>/', ListAllTeamMembers.as_view(), name='List_all_team_members'),
]
