from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import Branch, User
from .permissions import has_role
from .serializers import BranchSerializer, MeSerializer


@api_view(["GET"])
def me(request):
    return Response(MeSerializer(request.user).data)


@api_view(["GET"])
@permission_classes([has_role(User.Role.ADMIN, User.Role.FINANCE, User.Role.BRANCH_MANAGER)])
def agents(request):
    users = User.objects.filter(role=User.Role.AGENT, is_active=True).select_related("branch")
    if request.user.role == User.Role.BRANCH_MANAGER:
        users = users.filter(branch=request.user.branch_id)
    return Response([{"id": u.id, "name": u.get_full_name() or u.username, "branch": u.branch.name} for u in users])


@api_view(["GET"])
def branches(request):
    return Response(BranchSerializer(Branch.objects.all(), many=True).data)
