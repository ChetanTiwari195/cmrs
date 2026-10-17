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


class CashSubmission(models.Model):
    """Cash an agent hands over to their branch. The manager counts it and approves or rejects it."""

    class Status(models.TextChoices):
        PENDING = "PENDING"
        APPROVED = "APPROVED"
        REJECTED = "REJECTED"

    agent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="cash_submissions")
    branch = models.ForeignKey("accounts.Branch", on_delete=models.PROTECT, related_name="cash_submissions")
    # Many-to-many so a rejected submission keeps its history when the same collections are resubmitted.
    collections = models.ManyToManyField(Collection, related_name="submissions")
    expected_amount = models.DecimalField(**MONEY)
    received_amount = models.DecimalField(**MONEY, null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    remarks = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.CheckConstraint(condition=Q(received_amount__isnull=True) | Q(received_amount__gte=0), name="submission_received_non_negative")]

    @property
    def ref_no(self):
        return f"CS{self.pk:06d}"

    def __str__(self):
        return self.ref_no


class Discrepancy(models.Model):
    """A recorded difference between what was expected and what actually arrived."""

    class Type(models.TextChoices):
        SHORT = "SHORT"  # branch received less cash than collected
        EXCESS = "EXCESS"  # branch received more cash than collected
        BANK_MISMATCH = "BANK_MISMATCH"  # bank settled a different amount than deposited

    class Status(models.TextChoices):
        OPEN = "OPEN"
        RESOLVED = "RESOLVED"

    type = models.CharField(max_length=20, choices=Type.choices)
    branch = models.ForeignKey("accounts.Branch", on_delete=models.PROTECT, related_name="discrepancies")
    submission = models.ForeignKey(CashSubmission, null=True, blank=True, on_delete=models.PROTECT, related_name="discrepancies")
    expected = models.DecimalField(**MONEY)
    actual = models.DecimalField(**MONEY)
    difference = models.DecimalField(**MONEY, help_text="expected - actual; positive means money is missing")
    note = models.TextField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    resolution_note = models.TextField(blank=True)
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "discrepancies"
