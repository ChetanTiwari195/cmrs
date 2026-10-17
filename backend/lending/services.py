import calendar
from datetime import date
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal

from django.db import transaction

from audit.models import log_action

from .models import Installment, Loan

PAISA = Decimal("0.01")


def add_months(d, months):
    month = d.month - 1 + months
    year, month = d.year + month // 12, month % 12 + 1
    return date(year, month, min(d.day, calendar.monthrange(year, month)[1]))


def flat_schedule(principal, annual_rate, tenure_months):
    """Flat interest: interest on the full principal for the whole tenure, split evenly.
    The last EMI takes the rounding remainder so the schedule adds up exactly."""
    interest = (principal * annual_rate * tenure_months / Decimal(1200)).quantize(PAISA, ROUND_HALF_UP)
    total = principal + interest
    emi = (total / tenure_months).quantize(PAISA, ROUND_DOWN)
    amounts = [emi] * (tenure_months - 1) + [total - emi * (tenure_months - 1)]
    return interest, total, amounts


@transaction.atomic
def create_loan(user, customer, principal, annual_rate, tenure_months, disbursed_on):
    interest, total, amounts = flat_schedule(principal, annual_rate, tenure_months)
    loan = Loan.objects.create(
        customer=customer,
        principal=principal,
        annual_rate=annual_rate,
        tenure_months=tenure_months,
        disbursed_on=disbursed_on,
        total_interest=interest,
        total_payable=total,
        created_by=user,
    )
    Installment.objects.bulk_create(
        Installment(loan=loan, seq=i, due_date=add_months(disbursed_on, i), amount_due=amount)
        for i, amount in enumerate(amounts, start=1)
    )
    log_action(user, "CREATE", loan, after={"loan_no": loan.loan_no, "principal": str(principal), "total_payable": str(total)})
    return loan
