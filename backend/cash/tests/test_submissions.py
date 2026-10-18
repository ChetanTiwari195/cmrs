from decimal import Decimal

from django.test import TestCase

from cash.models import CashSubmission, Collection, Discrepancy

from .helpers import Fixtures


class SubmissionTests(Fixtures, TestCase):
    def setUp(self):
        self.collect("3000")
        self.collect("2000")

    def submit(self, user=None):
        return self.api(user or self.agent).post("/api/v1/submissions/")

    def approve(self, sid, received, remarks="", user=None):
        return self.api(user or self.manager).post(f"/api/v1/submissions/{sid}/approve/", {"received_amount": received, "remarks": remarks})

    def statuses(self):
        return set(Collection.objects.values_list("status", flat=True))

    def test_submit_all_cash_in_hand(self):
        res = self.submit()
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual((res.data["expected_amount"], res.data["collection_count"]), ("5000.00", 2))
        self.assertEqual(self.statuses(), {Collection.Status.SUBMITTED})
        self.assertEqual(self.submit().status_code, 400)  # nothing left to submit

    def test_only_agents_submit(self):
        self.assertEqual(self.submit(self.manager).status_code, 403)

    def test_approve_exact_amount(self):
        sid = self.submit().data["id"]
        res = self.approve(sid, "5000")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["status"], "APPROVED")
        self.assertEqual(self.statuses(), {Collection.Status.BRANCH_RECEIVED})
        self.assertFalse(Discrepancy.objects.exists())

    def test_short_cash_records_discrepancy(self):
        sid = self.submit().data["id"]
        self.assertEqual(self.approve(sid, "4850").status_code, 400)  # remarks required
        res = self.approve(sid, "4850", "Agent short by 150, will recover")
        self.assertEqual(res.data["difference"], "150.00")
        d = Discrepancy.objects.get()
        self.assertEqual((d.type, d.expected, d.actual, d.difference), ("SHORT", Decimal("5000"), Decimal("4850"), Decimal("150")))

    def test_excess_cash_records_discrepancy(self):
        sid = self.submit().data["id"]
        self.approve(sid, "5100", "Extra note found")
        self.assertEqual(Discrepancy.objects.get().type, "EXCESS")
        self.assertEqual(Discrepancy.objects.get().difference, Decimal("-100"))

    def test_reject_returns_cash_to_agent_and_keeps_history(self):
        sid = self.submit().data["id"]
        self.assertEqual(self.api(self.manager).post(f"/api/v1/submissions/{sid}/reject/", {"remarks": ""}).status_code, 400)
        res = self.api(self.manager).post(f"/api/v1/submissions/{sid}/reject/", {"remarks": "Count mismatch, recount"})
        self.assertEqual(res.data["status"], "REJECTED")
        self.assertEqual(self.statuses(), {Collection.Status.COLLECTED})
        self.assertEqual(self.submit().status_code, 201)  # resubmit
        self.assertEqual(CashSubmission.objects.get(pk=sid).collections.count(), 2)

    def test_reviewed_submission_is_locked(self):
        sid = self.submit().data["id"]
        self.approve(sid, "5000")
        self.assertEqual(self.approve(sid, "4000", "again").status_code, 400)
        self.assertEqual(self.api(self.manager).post(f"/api/v1/submissions/{sid}/reject/", {"remarks": "x"}).status_code, 400)
        self.assertEqual(self.api(self.manager).patch(f"/api/v1/submissions/{sid}/", {"received_amount": "1"}).status_code, 405)

    def test_other_branch_manager_cannot_review(self):
        sid = self.submit().data["id"]
        self.assertEqual(self.approve(sid, "5000", user=self.other_manager).status_code, 404)
        self.assertEqual(self.approve(sid, "5000", user=self.agent).status_code, 403)

    def test_resolve_discrepancy(self):
        sid = self.submit().data["id"]
        self.approve(sid, "4900", "short")
        did = Discrepancy.objects.get().id
        client = self.api(self.manager)
        self.assertEqual(client.post(f"/api/v1/discrepancies/{did}/resolve/", {"resolution_note": ""}).status_code, 400)
        res = client.post(f"/api/v1/discrepancies/{did}/resolve/", {"resolution_note": "Recovered from agent"})
        self.assertEqual(res.data["status"], "RESOLVED")
        self.assertEqual(self.api(self.agent).post(f"/api/v1/discrepancies/{did}/resolve/", {"resolution_note": "x"}).status_code, 403)
        self.assertEqual(self.api(self.other_manager).get("/api/v1/discrepancies/").data, [])


class SubmissionListTests(Fixtures, TestCase):
    def test_list_shows_receipts_and_totals_per_agent(self):
        self.collect("3000")
        self.collect("2000")
        sid = self.api(self.agent).post("/api/v1/submissions/").data["id"]
        self.api(self.manager).post(f"/api/v1/submissions/{sid}/approve/", {"received_amount": "4850", "remarks": "short"})
        self.collect("700")
        self.api(self.agent).post("/api/v1/submissions/")

        data = self.api(self.manager).get("/api/v1/submissions/").data
        approved = next(s for s in data["results"] if s["id"] == sid)
        self.assertEqual([r["amount"] for r in approved["receipts"]], ["3000.00", "2000.00"])
        self.assertTrue(approved["receipts"][0]["receipt_no"].startswith("RC"))
        self.assertEqual(data["by_agent"], [{
            "agent": self.agent.id, "expected": Decimal("5700"), "received": Decimal("4850"),
            "difference": Decimal("150"), "receipts": 3,
        }])
        self.assertEqual(data["total"]["expected"], Decimal("5700"))
        self.assertEqual(self.api(self.other_manager).get("/api/v1/submissions/").data["total"]["receipts"], 0)
