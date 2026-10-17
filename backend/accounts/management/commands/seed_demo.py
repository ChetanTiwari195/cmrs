import os

from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import Branch, User

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
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(BRANCHES)} branches and {len(USERS)} users."))
