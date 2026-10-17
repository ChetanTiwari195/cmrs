from rest_framework.permissions import BasePermission

from .models import User


def has_role(*roles):
    class HasRole(BasePermission):
        def has_permission(self, request, view):
            return request.user.is_authenticated and request.user.role in roles

    return HasRole


IsAdmin = has_role(User.Role.ADMIN)
IsFinance = has_role(User.Role.FINANCE)
IsBranchManager = has_role(User.Role.BRANCH_MANAGER)
IsAgent = has_role(User.Role.AGENT)
