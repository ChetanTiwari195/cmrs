from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import User
from .permissions import IsAdmin
from .serializers import MeSerializer


@api_view(["GET"])
def me(request):
    return Response(MeSerializer(request.user).data)


@api_view(["GET"])
@permission_classes([IsAdmin])
def agents(request):
    users = User.objects.filter(role=User.Role.AGENT, is_active=True).select_related("branch")
    return Response([{"id": u.id, "name": u.get_full_name() or u.username, "branch": u.branch.name} for u in users])
