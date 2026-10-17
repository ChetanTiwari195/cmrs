from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from audit.models import log_action
from lending.models import Installment, Loan

from .models import CashSubmission, Collection, Discrepancy


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


def _get_pending_submission(submission_id):
    submission = CashSubmission.objects.select_for_update().get(pk=submission_id)
    if submission.status != CashSubmission.Status.PENDING:
        raise ValidationError({"status": f"This submission is already {submission.status.lower()}."})
    return submission


@transaction.atomic
def submit_cash(agent):
    """Hand over all cash the agent currently holds to their branch."""
    collections = list(Collection.objects.select_for_update().filter(agent=agent, status=Collection.Status.COLLECTED))
    if not collections:
        raise ValidationError({"detail": "You have no collected cash to submit."})
    submission = CashSubmission.objects.create(
        agent=agent, branch=agent.branch, expected_amount=sum(c.amount for c in collections)
    )
    submission.collections.set(collections)
    Collection.objects.filter(pk__in=[c.pk for c in collections]).update(status=Collection.Status.SUBMITTED)
    log_action(agent, "SUBMIT_CASH", submission, after={"expected": str(submission.expected_amount), "collections": len(collections)})
    return submission


@transaction.atomic
def approve_submission(manager, submission_id, received_amount, remarks):
    submission = _get_pending_submission(submission_id)
    difference = submission.expected_amount - received_amount
    if difference and not remarks.strip():
        raise ValidationError({"remarks": "Remarks are required when the received amount differs from the expected amount."})

    submission.received_amount = received_amount
    submission.remarks = remarks
    submission.status = CashSubmission.Status.APPROVED
    submission.reviewed_by = manager
    submission.reviewed_at = timezone.now()
    submission.save()
    submission.collections.update(status=Collection.Status.BRANCH_RECEIVED)

    if difference:
        Discrepancy.objects.create(
            type=Discrepancy.Type.SHORT if difference > 0 else Discrepancy.Type.EXCESS,
            branch=submission.branch,
            submission=submission,
            expected=submission.expected_amount,
            actual=received_amount,
            difference=difference,
            note=remarks,
        )
    log_action(manager, "APPROVE_CASH", submission, after={"expected": str(submission.expected_amount), "received": str(received_amount)})
    return submission


@transaction.atomic
def reject_submission(manager, submission_id, remarks):
    if not remarks.strip():
        raise ValidationError({"remarks": "A reason is required to reject a submission."})
    submission = _get_pending_submission(submission_id)
    submission.remarks = remarks
    submission.status = CashSubmission.Status.REJECTED
    submission.reviewed_by = manager
    submission.reviewed_at = timezone.now()
    submission.save()
    # The cash goes back to the agent, who can fix the problem and submit again.
    submission.collections.update(status=Collection.Status.COLLECTED)
    log_action(manager, "REJECT_CASH", submission, after={"remarks": remarks})
    return submission


@transaction.atomic
def resolve_discrepancy(user, discrepancy_id, resolution_note):
    if not resolution_note.strip():
        raise ValidationError({"resolution_note": "Explain how this was resolved."})
    discrepancy = Discrepancy.objects.select_for_update().get(pk=discrepancy_id)
    if discrepancy.status == Discrepancy.Status.RESOLVED:
        raise ValidationError({"status": "Already resolved."})
    discrepancy.status = Discrepancy.Status.RESOLVED
    discrepancy.resolution_note = resolution_note
    discrepancy.resolved_by = user
    discrepancy.resolved_at = timezone.now()
    discrepancy.save()
    log_action(user, "RESOLVE_DISCREPANCY", discrepancy, after={"note": resolution_note})
    return discrepancy
