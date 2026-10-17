from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from .helpers import Fixtures

TODAY = timezone.localdate()


class DashboardTests(Fixtures, TestCase):
    """Fixture loan: ₹12,000 over 12 EMIs of ₹1,000, disbursed 2026-01-01."""

    def setUp(self):
        # Batch 1: ₹3,000 collected, branch counts ₹2,900, deposited, bank settles ₹2,900.
        self.collect("3000")
        sid = self.api(self.agent).post("/api/v1/submissions/").data["id"]
        self.api(self.manager).post(f"/api/v1/submissions/{sid}/approve/", {"received_amount": "2900", "remarks": "short"})
        did = self.api(self.manager).post(
            "/api/v1/deposits/", {"bank_name": "SBI", "reference": "R1", "amount": "2900", "deposit_date": TODAY}
        ).data["id"]
        self.api(self.finance).post(f"/api/v1/deposits/{did}/settle/", {"settled_amount": "2900", "settled_on": TODAY})
        # Batch 2: ₹500 submitted, not yet reviewed. Batch 3: ₹200 still with the agent.
        self.collect("500")
        self.api(self.agent).post("/api/v1/submissions/")
        self.collect("200")

    def summary(self, user, **params):
        return self.api(user).get("/api/v1/dashboard/", params).data

    def test_numbers_follow_the_money(self):
        data = self.summary(self.finance)
        expected = {
            "collected": "3700", "with_agents": "700", "received_at_branch": "2900", "deposited": "2900",
            "settled": "2900", "outstanding": "8300", "expected": "12000", "open_discrepancies": 1,
            "open_discrepancy_amount": "100", "pending_deposits": 0,
        }
        for key, value in expected.items():
            self.assertEqual(data[key], Decimal(value) if isinstance(value, str) else value, key)
        self.assertEqual(data["by_agent"][0]["held"], Decimal("700"))

    def test_date_filter(self):
        future = self.summary(self.finance, date_from=TODAY + timedelta(days=1))
        self.assertEqual((future["collected"], future["settled"]), (Decimal("0"), Decimal("0")))
        # Outstanding is the current position, so it ignores the date range.
        self.assertEqual(future["outstanding"], Decimal("8300"))

    def test_branch_scope(self):
        self.assertEqual(self.summary(self.finance, branch=self.other_branch.id)["collected"], Decimal("0"))
        # A manager can't look at another branch by passing its id.
        self.assertEqual(self.summary(self.manager, branch=self.other_branch.id)["collected"], Decimal("3700"))
        self.assertEqual(self.summary(self.other_manager)["collected"], Decimal("0"))

    def test_agent_sees_own_numbers(self):
        self.assertEqual(self.summary(self.agent)["collected"], Decimal("3700"))
        self.assertEqual(self.summary(self.other_agent)["collected"], Decimal("0"))
        self.assertEqual(self.summary(self.finance, agent=self.other_agent.id)["collected"], Decimal("0"))
