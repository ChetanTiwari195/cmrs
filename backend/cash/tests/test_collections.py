import uuid
from decimal import Decimal

from django.test import TestCase

from cash.models import Collection
from lending.models import Installment, Loan

from .helpers import Fixtures


class CollectionTests(Fixtures, TestCase):
    def installments(self):
        return list(self.loan.installments.order_by("seq").values_list("amount_paid", "status")[:3])

    def test_partial_payment(self):
        res = self.collect("400")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertTrue(res.data["receipt_no"].startswith("RC"))
        self.assertEqual(self.installments()[0], (Decimal("400.00"), Installment.Status.PARTIAL))

    def test_extra_amount_goes_to_next_emis(self):
        self.collect("2500")
        self.assertEqual(self.installments(), [
            (Decimal("1000.00"), Installment.Status.PAID),
            (Decimal("1000.00"), Installment.Status.PAID),
            (Decimal("500.00"), Installment.Status.PARTIAL),
        ])

    def test_over_collection_rejected_with_difference(self):
        self.collect("11000")
        res = self.collect("1500")
        self.assertEqual(res.status_code, 400)
        self.assertIn("₹500.00 more than the outstanding ₹1000.00", str(res.data["amount"]))
        self.assertEqual(Collection.objects.count(), 1)

    def test_full_payment_closes_loan(self):
        self.collect("12000")
        self.loan.refresh_from_db()
        self.assertEqual(self.loan.status, Loan.Status.CLOSED)
        self.assertEqual(self.collect("1").status_code, 400)

    def test_duplicate_request_is_not_counted_twice(self):
        key = uuid.uuid4()
        first = self.collect("700", key=key)
        second = self.collect("700", key=key)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.data["id"], second.data["id"])
        self.assertEqual(self.installments()[0][0], Decimal("700.00"))

    def test_invalid_amounts_rejected(self):
        for amount in ["0", "-5", "10.123"]:
            self.assertEqual(self.collect(amount).status_code, 400, amount)

    def test_only_assigned_agent_can_collect(self):
        self.assertEqual(self.collect("100", user=self.other_agent).status_code, 403)
        self.assertEqual(self.collect("100", user=self.manager).status_code, 403)

    def test_collections_are_read_only(self):
        cid = self.collect("100").data["id"]
        client = self.api(self.agent)
        self.assertEqual(client.patch(f"/api/v1/collections/{cid}/", {"amount": "1"}).status_code, 405)
        self.assertEqual(client.delete(f"/api/v1/collections/{cid}/").status_code, 405)

    def test_list_scoped_with_total(self):
        self.collect("100")
        self.collect("250.50")
        data = self.api(self.agent).get("/api/v1/collections/", {"loan": self.loan.id}).data
        self.assertEqual((data["count"], data["total"]), (2, Decimal("350.50")))
        self.assertEqual(self.api(self.manager).get("/api/v1/collections/").data["count"], 2)
        self.assertEqual(self.api(self.other_manager).get("/api/v1/collections/").data["count"], 0)
        self.assertEqual(self.api(self.other_agent).get("/api/v1/collections/").data["count"], 0)
