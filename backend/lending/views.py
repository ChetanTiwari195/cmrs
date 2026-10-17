from django.db.models import DecimalField, F, Sum, Value
from django.db.models.functions import Coalesce
from rest_framework import mixins, viewsets
from rest_framework.permissions import SAFE_METHODS, IsAuthenticated

from accounts.models import User
from accounts.permissions import IsAdmin
from audit.models import log_action

from . import services
from .models import Customer, Loan
from .serializers import CustomerSerializer, LoanDetailSerializer, LoanSerializer


def scope(qs, user, customer_path=""):
    """Limit rows to what the user may see: agents their customers, managers their branch."""
    if user.role == User.Role.AGENT:
        return qs.filter(**{f"{customer_path}assigned_agent": user})
    if user.role == User.Role.BRANCH_MANAGER:
        return qs.filter(**{f"{customer_path}branch": user.branch_id})
    return qs


class AdminWritesMixin:
    def get_permissions(self):
        return [IsAuthenticated()] if self.request.method in SAFE_METHODS else [IsAdmin()]


class CustomerViewSet(AdminWritesMixin, mixins.CreateModelMixin, mixins.UpdateModelMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = CustomerSerializer

    def get_queryset(self):
        return scope(Customer.objects.select_related("branch", "assigned_agent"), self.request.user)

    def perform_create(self, serializer):
        customer = serializer.save(branch=serializer.validated_data["assigned_agent"].branch)
        log_action(self.request.user, "CREATE", customer, after=serializer.data)

    def perform_update(self, serializer):
        before = CustomerSerializer(serializer.instance).data
        customer = serializer.save(branch=serializer.validated_data.get("assigned_agent", serializer.instance.assigned_agent).branch)
        log_action(self.request.user, "UPDATE", customer, before=before, after=serializer.data)


class LoanViewSet(AdminWritesMixin, mixins.CreateModelMixin, viewsets.ReadOnlyModelViewSet):
    def get_serializer_class(self):
        return LoanDetailSerializer if self.action == "retrieve" else LoanSerializer

    def get_queryset(self):
        qs = Loan.objects.select_related("customer").annotate(
            amount_paid=Coalesce(Sum("installments__amount_paid"), Value(0), output_field=DecimalField()),
            outstanding=F("total_payable") - F("amount_paid"),
        )
        if self.action == "retrieve":
            qs = qs.prefetch_related("installments")
        return scope(qs, self.request.user, "customer__")

    def perform_create(self, serializer):
        loan = services.create_loan(self.request.user, **serializer.validated_data)
        serializer.instance = self.get_queryset().get(pk=loan.pk)
