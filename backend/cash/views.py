from django.db.models import Count, Sum
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import User
from accounts.permissions import IsAgent, IsBranchManager, IsFinance, has_role

from . import services
from .filters import CollectionFilter
from .models import BankDeposit, CashSubmission, Collection, Discrepancy
from .serializers import (
    ApproveSerializer, BankDepositSerializer, SettleSerializer, CashSubmissionSerializer, CollectionSerializer, DiscrepancySerializer, RemarksSerializer,
    ResolveSerializer,
)


def scope(qs, user, agent_field="agent", branch_field="branch"):
    """Agents see their own rows, managers their branch, admin and finance everything."""
    if user.role == User.Role.AGENT:
        return qs.filter(**{agent_field: user})
    if user.role == User.Role.BRANCH_MANAGER:
        return qs.filter(**{branch_field: user.branch_id})
    return qs


class CollectionViewSet(mixins.CreateModelMixin, viewsets.ReadOnlyModelViewSet):
    """Collections can be created and read, never edited or deleted."""

    serializer_class = CollectionSerializer
    filterset_class = CollectionFilter

    def get_permissions(self):
        return [IsAgent()] if self.action == "create" else [IsAuthenticated()]

    def get_queryset(self):
        qs = Collection.objects.select_related("loan__customer", "agent")
        return scope(qs, self.request.user, branch_field="loan__customer__branch")

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


class CashSubmissionViewSet(mixins.CreateModelMixin, viewsets.ReadOnlyModelViewSet):
    """Agents submit all the cash they hold; the branch manager approves or rejects it. No edits after that."""

    serializer_class = CashSubmissionSerializer
    filterset_fields = ["status", "agent", "branch"]

    def get_permissions(self):
        if self.action == "create":
            return [IsAgent()]
        if self.action in ("approve", "reject"):
            return [IsBranchManager()]
        return [IsAuthenticated()]

    def get_queryset(self):
        qs = CashSubmission.objects.select_related("agent", "branch", "reviewed_by").annotate(collection_count=Count("collections"))
        return scope(qs, self.request.user)

    def create(self, request):
        submission = services.submit_cash(request.user)
        return Response(self.get_serializer(self.get_queryset().get(pk=submission.pk)).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        data = ApproveSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        services.approve_submission(request.user, self.get_object().pk, data.validated_data["received_amount"], data.validated_data["remarks"])
        return Response(self.get_serializer(self.get_object()).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        data = RemarksSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        services.reject_submission(request.user, self.get_object().pk, data.validated_data["remarks"])
        return Response(self.get_serializer(self.get_object()).data)


class DiscrepancyViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DiscrepancySerializer
    filterset_fields = ["status", "type", "branch"]

    def get_permissions(self):
        if self.action == "resolve":
            return [has_role(User.Role.BRANCH_MANAGER, User.Role.FINANCE, User.Role.ADMIN)()]
        return [IsAuthenticated()]

    def get_queryset(self):
        qs = Discrepancy.objects.select_related("branch", "submission", "deposit", "resolved_by")
        return scope(qs, self.request.user, agent_field="submission__agent")

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        data = ResolveSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        services.resolve_discrepancy(request.user, self.get_object().pk, data.validated_data["resolution_note"])
        return Response(self.get_serializer(self.get_object()).data)


class BankDepositViewSet(mixins.CreateModelMixin, viewsets.ReadOnlyModelViewSet):
    """Managers deposit reconciled cash; finance settles or fails it. No edits."""

    serializer_class = BankDepositSerializer
    filterset_fields = ["status", "branch"]

    def get_permissions(self):
        if self.action in ("create", "eligible"):
            return [IsBranchManager()]
        if self.action in ("settle", "fail"):
            return [IsFinance()]
        return [IsAuthenticated()]

    def get_queryset(self):
        qs = BankDeposit.objects.select_related("branch").prefetch_related("submissions")
        if self.request.user.role == User.Role.AGENT:
            return qs.none()
        return scope(qs, self.request.user)

    def perform_create(self, serializer):
        serializer.instance = services.create_deposit(self.request.user, **serializer.validated_data)

    @action(detail=False)
    def eligible(self, request):
        """Reconciled cash the manager's branch can deposit right now."""
        submissions = services.depositable_submissions(request.user.branch_id)
        totals = submissions.aggregate(total=Sum("received_amount"), count=Count("id"))
        return Response({"total": totals["total"] or "0.00", "count": totals["count"], "refs": [s.ref_no for s in submissions]})

    @action(detail=True, methods=["post"])
    def settle(self, request, pk=None):
        data = SettleSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        services.settle_deposit(request.user, self.get_object().pk, **data.validated_data)
        return Response(self.get_serializer(self.get_object()).data)

    @action(detail=True, methods=["post"])
    def fail(self, request, pk=None):
        data = RemarksSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        services.fail_deposit(request.user, self.get_object().pk, data.validated_data["remarks"])
        return Response(self.get_serializer(self.get_object()).data)
