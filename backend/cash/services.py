from decimal import Decimal

from django.db import IntegrityError, transaction
from rest_framework.exceptions import PermissionDenied, ValidationError

from audit.models import log_action
from lending.models import Installment, Loan

from .models import Collection


def collect_payment(agent, loan_id, amount, idempotency_key):
    """Record a cash repayment and apply it to the oldest unpaid EMIs first.
    Returns (collection, created). A repeated idempotency key returns the original collection."""
    existing = Collection.objects.filter(idempotency_key=idempotency_key).first()
    if existing:
        if existing.agent_id != agent.id:
            raise ValidationError({"idempotency_key": "This key was already used."})
        return existing, False
    try:
        return _collect(agent, loan_id, amount, idempotency_key), True
    except IntegrityError:
        # Lost a race with the same request; the other one created it.
        return Collection.objects.get(idempotency_key=idempotency_key, agent=agent), False


@transaction.atomic
def _collect(agent, loan_id, amount, idempotency_key):
    loan = Loan.objects.select_for_update().select_related("customer").filter(pk=loan_id).first()
    if not loan or loan.customer.assigned_agent_id != agent.id:
        raise PermissionDenied("You can only collect for your assigned customers.")
    if loan.status != Loan.Status.ACTIVE:
        raise ValidationError({"loan": "This loan is already closed."})

    installments = list(loan.installments.exclude(status=Installment.Status.PAID).order_by("seq"))
    outstanding = sum((i.amount_due - i.amount_paid for i in installments), Decimal(0))
    if amount > outstanding:
        raise ValidationError({
            "amount": f"Over-collection: ₹{amount} is ₹{amount - outstanding} more than the outstanding ₹{outstanding}. Payment rejected."
        })

    collection = Collection.objects.create(loan=loan, agent=agent, amount=amount, idempotency_key=idempotency_key)

    remaining = amount
    for inst in installments:
        if not remaining:
            break
        applied = min(remaining, inst.amount_due - inst.amount_paid)
        inst.amount_paid += applied
        inst.status = Installment.Status.PAID if inst.amount_paid == inst.amount_due else Installment.Status.PARTIAL
        remaining -= applied
    Installment.objects.bulk_update(installments, ["amount_paid", "status"])

    if amount == outstanding:
        loan.status = Loan.Status.CLOSED
        loan.save(update_fields=["status"])

    log_action(agent, "COLLECT", collection, after={"loan": loan.loan_no, "amount": str(amount)})
    return collection
