from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from cash.models import BankDeposit, Collection, Discrepancy

from .helpers import Fixtures

TODAY = timezone.localdate()


class DepositTests(Fixtures, TestCase):
    def reconcile(self, amount, received=None):
        """Collect, submit and approve one batch of cash at the branch."""
        self.collect(amount)
        sid = self.api(self.agent).post("/api/v1/submissions/").data["id"]
        received = received or amount
        self.api(self.manager).post(f"/api/v1/submissions/{sid}/approve/", {"received_amount": received, "remarks": "short" if received != amount else ""})

    def deposit(self, amount, reference="UTR001", bank="HDFC Bank", user=None, deposit_date=TODAY):
        return self.api(user or self.manager).post(
            "/api/v1/deposits/", {"bank_name": bank, "reference": reference, "amount": amount, "deposit_date": deposit_date}
        )

    def settle(self, did, amount, remarks=""):
        return self.api(self.finance).post(f"/api/v1/deposits/{did}/settle/", {"settled_amount": amount, "settled_on": TODAY, "remarks": remarks})

    def statuses(self):
        return set(Collection.objects.values_list("status", flat=True))

    def test_eligible_uses_received_amounts(self):
        self.reconcile("3000", received="2900")
        self.reconcile("1000")
        data = self.api(self.manager).get("/api/v1/deposits/eligible/").data
        self.assertEqual((data["total"], data["count"]), (Decimal("3900"), 2))

    def test_full_lifecycle_to_settled(self):
        self.reconcile("5000")
        res = self.deposit("5000")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(self.statuses(), {Collection.Status.DEPOSITED})
        self.assertEqual(self.settle(res.data["id"], "5000").data["status"], "SETTLED")
        self.assertEqual(self.statuses(), {Collection.Status.SETTLED})
        self.assertFalse(Discrepancy.objects.exists())

    def test_deposit_amount_must_match(self):
        self.reconcile("5000")
        res = self.deposit("4999")
        self.assertEqual(res.status_code, 400)
        self.assertIn("Deposit mismatch", str(res.data["amount"]))

    def test_nothing_to_deposit(self):
        self.assertEqual(self.deposit("100").status_code, 400)

    def test_duplicate_bank_reference(self):
        self.reconcile("1000")
        self.assertEqual(self.deposit("1000", reference="utr-9").status_code, 201)
        self.reconcile("2000")
        res = self.deposit("2000", reference=" UTR-9 ", bank="hdfc  bank")
        self.assertEqual(res.status_code, 400)
        self.assertIn("already recorded", str(res.data["reference"]))
        self.assertEqual(self.deposit("2000", reference="UTR-9", bank="SBI").status_code, 201)

    def test_bank_settles_less_creates_mismatch(self):
        self.reconcile("5000")
        did = self.deposit("5000").data["id"]
        self.assertEqual(self.settle(did, "4800").status_code, 400)  # remarks required
        res = self.settle(did, "4800", "Bank charges deducted")
        self.assertEqual(res.data["difference"], "200.00")
        d = Discrepancy.objects.get()
        self.assertEqual((d.type, d.difference, d.deposit_id), ("BANK_MISMATCH", Decimal("200"), did))

    def test_failed_deposit_releases_cash(self):
        self.reconcile("5000")
        did = self.deposit("5000").data["id"]
        res = self.api(self.finance).post(f"/api/v1/deposits/{did}/fail/", {"remarks": "Cheque bounced"})
        self.assertEqual(res.data["status"], "FAILED")
        self.assertEqual(self.statuses(), {Collection.Status.BRANCH_RECEIVED})
        self.assertEqual(self.deposit("5000", reference="UTR002").status_code, 201)
        self.assertEqual(self.settle(did, "5000").status_code, 400)  # failed deposit is closed

    def test_delayed_flag(self):
        self.reconcile("5000")
        res = self.deposit("5000", deposit_date=TODAY - timedelta(days=5))
        self.assertTrue(res.data["is_delayed"])
        self.settle(res.data["id"], "5000")
        self.assertFalse(self.api(self.finance).get(f"/api/v1/deposits/{res.data['id']}/").data["is_delayed"])

    def test_permissions(self):
        self.reconcile("5000")
        self.assertEqual(self.deposit("5000", user=self.agent).status_code, 403)
        self.assertEqual(self.deposit("5000", user=self.other_manager).status_code, 400)  # nothing at their branch
        did = self.deposit("5000").data["id"]
        self.assertEqual(self.api(self.manager).post(f"/api/v1/deposits/{did}/settle/", {"settled_amount": "5000", "settled_on": TODAY}).status_code, 403)
        self.assertEqual(self.api(self.other_manager).get("/api/v1/deposits/").data, [])
        self.assertEqual(self.api(self.manager).patch(f"/api/v1/deposits/{did}/", {"amount": "1"}).status_code, 405)

    def test_future_dates_rejected(self):
        self.reconcile("5000")
        self.assertEqual(self.deposit("5000", deposit_date=TODAY + timedelta(days=1)).status_code, 400)
        did = self.deposit("5000").data["id"]
        res = self.api(self.finance).post(f"/api/v1/deposits/{did}/settle/", {"settled_amount": "5000", "settled_on": date(2000, 1, 1)})
        self.assertEqual(res.status_code, 400)
