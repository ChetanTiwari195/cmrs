from django.db.models import Count, DecimalField, F, Q, Sum, Value
from django.db.models.functions import Coalesce
from rest_framework.decorators import api_view
from rest_framework.response import Response

from accounts.models import User
from lending.models import Installment, Loan

from .models import BankDeposit, CashSubmission, Collection, Discrepancy

ZERO = Value(0, output_field=DecimalField(max_digits=14, decimal_places=2))


def total(qs, expr):
    return qs.aggregate(v=Coalesce(Sum(expr), ZERO))["v"]


def between(field, date_from, date_to):
    q = Q()
    if date_from:
        q &= Q(**{f"{field}__gte": date_from})
    if date_to:
        q &= Q(**{f"{field}__lte": date_to})
    return q


@api_view(["GET"])
def summary(request):
    """Where the money is, for a date range. Filters: date_from, date_to, branch, agent.
    Agents always see their own numbers and managers their own branch."""
    user, params = request.user, request.query_params
    date_from, date_to = params.get("date_from"), params.get("date_to")
    branch, agent = params.get("branch"), params.get("agent")
    if user.role == User.Role.BRANCH_MANAGER:
        branch = user.branch_id
    if user.role == User.Role.AGENT:
        agent = user.id

    def scoped(qs, branch_field, agent_field=None):
        if branch:
            qs = qs.filter(**{branch_field: branch})
        if agent:
            qs = qs.filter(**{agent_field: agent}) if agent_field else qs.none()
        return qs

    collections = scoped(Collection.objects.filter(between("collected_at__date", date_from, date_to)), "loan__customer__branch", "agent")
    installments = scoped(Installment.objects.all(), "loan__customer__branch", "loan__customer__assigned_agent")
    approved = scoped(
        CashSubmission.objects.filter(between("reviewed_at__date", date_from, date_to), status=CashSubmission.Status.APPROVED),
        "branch", "agent",
    )
    # Deposits are branch-level, so an agent filter leaves them empty.
    deposits = scoped(BankDeposit.objects.all(), "branch")
    discrepancies = scoped(Discrepancy.objects.filter(status=Discrepancy.Status.OPEN), "branch", "submission__agent")

    held = [Collection.Status.COLLECTED, Collection.Status.SUBMITTED]
    open_discrepancies = discrepancies.aggregate(count=Count("id"), amount=Coalesce(Sum("difference"), ZERO))
    by_agent = (
        collections.values("agent", "agent__first_name", "agent__username", "agent__branch__name")
        .annotate(collected=Sum("amount"), held=Coalesce(Sum("amount", filter=Q(status__in=held)), ZERO), receipts=Count("id"))
        .order_by("-collected")
    )

    return Response({
        "expected": total(installments.filter(between("due_date", date_from, date_to)), "amount_due"),
        "collected": total(collections, "amount"),
        "with_agents": total(collections.filter(status__in=held), "amount"),
        "received_at_branch": total(approved, "received_amount"),
        "deposited": total(
            deposits.filter(between("deposit_date", date_from, date_to)).exclude(status=BankDeposit.Status.FAILED), "amount"
        ),
        "settled": total(deposits.filter(between("settled_on", date_from, date_to), status=BankDeposit.Status.SETTLED), "settled_amount"),
        # Current position, not limited to the date range.
        "outstanding": total(installments.filter(loan__status=Loan.Status.ACTIVE), F("amount_due") - F("amount_paid")),
        "open_discrepancies": open_discrepancies["count"],
        "open_discrepancy_amount": open_discrepancies["amount"],
        "pending_deposits": deposits.filter(status=BankDeposit.Status.PENDING).count(),
        "by_agent": [
            {
                "agent": row["agent"],
                "name": row["agent__first_name"] or row["agent__username"],
                "branch": row["agent__branch__name"],
                "receipts": row["receipts"],
                "collected": row["collected"],
                "held": row["held"],
            }
            for row in by_agent
        ],
    })
