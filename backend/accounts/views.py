from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from audit.models import log_action

from .models import Branch, User
from .permissions import has_role
from .serializers import AgentCreateSerializer, BranchSerializer, MeSerializer


def agent_row(u):
    return {"id": u.id, "name": u.get_full_name() or u.username, "branch": u.branch.name}


@api_view(["GET"])
def me(request):
    return Response(MeSerializer(request.user).data)


@api_view(["GET", "POST"])
@permission_classes([has_role(User.Role.ADMIN, User.Role.FINANCE, User.Role.BRANCH_MANAGER)])
def agents(request):
    """List active agents, or (admin only) create a new collection agent."""
    if request.method == "POST":
        if request.user.role != User.Role.ADMIN:
            raise PermissionDenied("Only admins can add agents.")
        serializer = AgentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        agent = serializer.save()
        log_action(request.user, "CREATE_AGENT", agent, after={"username": agent.username, "branch": agent.branch.code})
        return Response(agent_row(agent), status=status.HTTP_201_CREATED)

    users = User.objects.filter(role=User.Role.AGENT, is_active=True).select_related("branch")
    if request.user.role == User.Role.BRANCH_MANAGER:
        users = users.filter(branch=request.user.branch_id)
    return Response([agent_row(u) for u in users])


@api_view(["GET"])
def branches(request):
    return Response(BranchSerializer(Branch.objects.all(), many=True).data)
