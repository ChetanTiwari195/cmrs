from django.conf import settings
from django.db import models
from django.db.models import Q

from lending.models import Loan

MONEY = {"max_digits": 14, "decimal_places": 2}


class Collection(models.Model):
    """One cash repayment collected by an agent. Its status follows the cash: agent -> branch -> bank."""

    class Status(models.TextChoices):
        COLLECTED = "COLLECTED"  # cash is with the agent
        SUBMITTED = "SUBMITTED"  # handed to the branch, awaiting verification
        BRANCH_RECEIVED = "BRANCH_RECEIVED"
        DEPOSITED = "DEPOSITED"
        SETTLED = "SETTLED"

    loan = models.ForeignKey(Loan, on_delete=models.PROTECT, related_name="collections")
    agent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="collections")
    amount = models.DecimalField(**MONEY)
    collected_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.COLLECTED)
    # Sent by the client once per payment form; a retried request returns the original receipt.
    idempotency_key = models.UUIDField(unique=True)

    class Meta:
        ordering = ["-collected_at"]
        indexes = [models.Index(fields=["agent", "status"]), models.Index(fields=["collected_at"])]
        constraints = [models.CheckConstraint(condition=Q(amount__gt=0), name="collection_amount_positive")]

    @property
    def receipt_no(self):
        return f"RC{self.collected_at:%y%m%d}{self.pk:06d}"

    def __str__(self):
        return self.receipt_no
