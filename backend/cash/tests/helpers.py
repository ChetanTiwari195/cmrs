import uuid
from datetime import date
from decimal import Decimal

from rest_framework.test import APIClient

from accounts.models import Branch, User
from lending.models import Customer
from lending.services import create_loan


class Fixtures:
    """Small world: one branch with an agent, a manager and a customer holding a ₹12,000 loan (12 x ₹1,000, 0%)."""

    @classmethod
    def setUpTestData(cls):
        cls.branch = Branch.objects.create(code="B1", name="Branch One")
        cls.other_branch = Branch.objects.create(code="B2", name="Branch Two")
        cls.admin = User.objects.create_user("admin", role=User.Role.ADMIN)
        cls.finance = User.objects.create_user("finance", role=User.Role.FINANCE)
        cls.agent = User.objects.create_user("agent", role=User.Role.AGENT, branch=cls.branch)
        cls.other_agent = User.objects.create_user("agent2", role=User.Role.AGENT, branch=cls.other_branch)
        cls.manager = User.objects.create_user("manager", role=User.Role.BRANCH_MANAGER, branch=cls.branch)
        cls.other_manager = User.objects.create_user("manager2", role=User.Role.BRANCH_MANAGER, branch=cls.other_branch)
        customer = Customer.objects.create(name="C", phone="9000000001", branch=cls.branch, assigned_agent=cls.agent)
        cls.loan = create_loan(cls.admin, customer, Decimal("12000"), Decimal("0"), 12, date(2026, 1, 1))

    def api(self, user):
        client = APIClient()
        client.force_authenticate(user)
        return client

    def collect(self, amount, user=None, key=None):
        return self.api(user or self.agent).post(
            "/api/v1/collections/",
            {"loan": self.loan.id, "amount": str(amount), "idempotency_key": str(key or uuid.uuid4())},
            format="json",
        )
