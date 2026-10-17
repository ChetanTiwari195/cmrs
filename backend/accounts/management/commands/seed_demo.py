import os
import uuid
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import Branch, User
from cash import services as cash
from cash.models import Collection
from lending.models import Customer
from lending.services import create_loan

BRANCHES = [("BLR01", "Bengaluru Central"), ("MUM01", "Mumbai Andheri")]

# username, first name, role, branch code
USERS = [
    ("admin", "Asha", User.Role.ADMIN, None),
    ("finance", "Farhan", User.Role.FINANCE, None),
    ("manager_blr", "Meera", User.Role.BRANCH_MANAGER, "BLR01"),
    ("agent_blr", "Arjun", User.Role.AGENT, "BLR01"),
    ("manager_mum", "Mohan", User.Role.BRANCH_MANAGER, "MUM01"),
    ("agent_mum", "Anita", User.Role.AGENT, "MUM01"),
]

# name, phone, agent username, principal, annual rate %, tenure months, months since disbursal
CUSTOMERS = [
    ("Ravi Kumar", "9800000001", "agent_blr", "50000", "12", 12, 3),
    ("Sunita Rao", "9800000002", "agent_blr", "120000", "14", 24, 1),
    ("Imran Shaikh", "9800000003", "agent_mum", "30000", "10", 6, 2),
    ("Pooja Desai", "9800000004", "agent_mum", "75000", "13", 12, 0),
]


class Command(BaseCommand):
    help = "Create demo branches and one user per role. Safe to run repeatedly."

    @transaction.atomic
    def handle(self, *args, **options):
        password = os.environ.get("DEMO_PASSWORD", "Demo@12345")
        branches = {
            code: Branch.objects.update_or_create(code=code, defaults={"name": name})[0]
            for code, name in BRANCHES
        }
        for username, first_name, role, branch_code in USERS:
            user, _ = User.objects.update_or_create(
                username=username,
                defaults={
                    "first_name": first_name,
                    "role": role,
                    "branch": branches.get(branch_code),
                    "is_staff": role == User.Role.ADMIN,
                    "is_superuser": role == User.Role.ADMIN,
                },
            )
            user.set_password(password)
            user.save()

        admin = User.objects.get(username="admin")
        for name, phone, agent_username, principal, rate, tenure, months_ago in CUSTOMERS:
            agent = User.objects.get(username=agent_username)
            customer, _ = Customer.objects.update_or_create(
                phone=phone, defaults={"name": name, "assigned_agent": agent, "branch": agent.branch}
            )
            if not customer.loans.exists():
                create_loan(admin, customer, Decimal(principal), Decimal(rate), tenure, date.today() - timedelta(days=30 * months_ago))
        if not Collection.objects.exists():
            self.seed_money_flow()
        self.stdout.write(self.style.SUCCESS(
            f"Seeded {len(BRANCHES)} branches, {len(USERS)} users and {len(CUSTOMERS)} customers with loans and cash activity."
        ))

    def seed_money_flow(self):
        """Walk cash through every stage so each business case is visible in the demo."""
        u = {name: User.objects.get(username=name) for name in ("finance", "manager_blr", "agent_blr", "manager_mum", "agent_mum")}
        loan = {c.name.split()[0]: c.loans.get() for c in Customer.objects.filter(phone__in=[c[1] for c in CUSTOMERS])}
        today = date.today()

        def collect(agent, first_name, amount):
            cash.collect_payment(u[agent], loan[first_name].id, Decimal(amount), uuid.uuid4())

        # Bengaluru: short cash at the branch, then a clean deposit and settlement.
        collect("agent_blr", "Ravi", "4666.66")
        collect("agent_blr", "Sunita", "6400")
        collect("agent_blr", "Ravi", "1000")  # partial EMI
        s = cash.submit_cash(u["agent_blr"])
        cash.approve_submission(u["manager_blr"], s.id, Decimal("11966.66"), "Rs 100 short, agent to make good")
        d = cash.create_deposit(u["manager_blr"], "HDFC BANK", "UTR-BLR-001", Decimal("11966.66"), today - timedelta(days=1))
        cash.settle_deposit(u["finance"], d.id, Decimal("11966.66"), today, "")
        # A rejected handover goes back to the agent, who now holds cash to submit live in the demo.
        collect("agent_blr", "Sunita", "2000")
        s = cash.submit_cash(u["agent_blr"])
        cash.reject_submission(u["manager_blr"], s.id, "Bundle count did not match the receipts")
        collect("agent_blr", "Ravi", "500")

        # Mumbai: a delayed deposit, a bank settlement mismatch, and a submission awaiting review.
        collect("agent_mum", "Imran", "5250")
        s = cash.submit_cash(u["agent_mum"])
        cash.approve_submission(u["manager_mum"], s.id, Decimal("5250"), "")
        cash.create_deposit(u["manager_mum"], "SBI", "SBI-MUM-001", Decimal("5250"), today - timedelta(days=5))
        collect("agent_mum", "Pooja", "7062.50")
        s = cash.submit_cash(u["agent_mum"])
        cash.approve_submission(u["manager_mum"], s.id, Decimal("7062.50"), "")
        d = cash.create_deposit(u["manager_mum"], "ICICI BANK", "ICICI-MUM-002", Decimal("7062.50"), today - timedelta(days=1))
        cash.settle_deposit(u["finance"], d.id, Decimal("7000"), today, "Bank deducted cash handling charges")
        collect("agent_mum", "Imran", "3000")
        cash.submit_cash(u["agent_mum"])
