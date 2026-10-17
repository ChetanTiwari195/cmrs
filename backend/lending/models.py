from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.db.models import F, Q

from accounts.models import Branch


class Customer(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=10, unique=True, validators=[RegexValidator(r"^[6-9]\d{9}$", "Enter a valid 10-digit mobile number.")])
    address = models.TextField(blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="customers")
    assigned_agent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="customers")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Loan(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE"
        CLOSED = "CLOSED"

    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="loans")
    principal = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(1)])
    annual_rate = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(100)])
    tenure_months = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(360)])
    disbursed_on = models.DateField()
    total_interest = models.DecimalField(max_digits=14, decimal_places=2)
    total_payable = models.DecimalField(max_digits=14, decimal_places=2)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.CheckConstraint(condition=Q(principal__gt=0), name="loan_principal_positive")]

    @property
    def loan_no(self):
        return f"LN{self.pk:06d}"

    def __str__(self):
        return self.loan_no


class Installment(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING"
        PARTIAL = "PARTIAL"
        PAID = "PAID"

    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name="installments")
    seq = models.PositiveSmallIntegerField()
    due_date = models.DateField()
    amount_due = models.DecimalField(max_digits=14, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)

    class Meta:
        ordering = ["loan", "seq"]
        constraints = [
            models.UniqueConstraint(fields=["loan", "seq"], name="unique_installment_seq"),
            models.CheckConstraint(condition=Q(amount_paid__gte=0) & Q(amount_paid__lte=F("amount_due")), name="installment_paid_within_due"),
        ]
