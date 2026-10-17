from django.db.models import Count, Sum
from rest_framework import mixins, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import User
from accounts.permissions import IsAgent

from . import services
from .filters import CollectionFilter
from .models import Collection
from .serializers import CollectionSerializer


class CollectionViewSet(mixins.CreateModelMixin, viewsets.ReadOnlyModelViewSet):
    """Collections can be created and read, never edited or deleted."""

    serializer_class = CollectionSerializer
    filterset_class = CollectionFilter

    def get_permissions(self):
        return [IsAgent()] if self.action == "create" else [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        qs = Collection.objects.select_related("loan__customer", "agent")
        if user.role == User.Role.AGENT:
            return qs.filter(agent=user)
        if user.role == User.Role.BRANCH_MANAGER:
            return qs.filter(loan__customer__branch=user.branch_id)
        return qs

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        totals = qs.aggregate(total=Sum("amount"), count=Count("id"))
        return Response({"total": totals["total"] or "0.00", "count": totals["count"], "results": self.get_serializer(qs, many=True).data})

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        collection, created = services.collect_payment(request.user, data["loan"].pk, data["amount"], data["idempotency_key"])
        return Response(self.get_serializer(collection).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
