import os
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import Branch, User
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
        self.stdout.write(self.style.SUCCESS(
            f"Seeded {len(BRANCHES)} branches, {len(USERS)} users and {len(CUSTOMERS)} customers with loans."
        ))
