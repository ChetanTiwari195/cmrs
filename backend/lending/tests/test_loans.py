from datetime import date
from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from lending.models import Customer, Loan
from lending.services import add_months, flat_schedule


class ScheduleTests(TestCase):
    def test_flat_interest_schedule_adds_up_exactly(self):
        interest, total, amounts = flat_schedule(Decimal("100000"), Decimal("12"), 12)
        self.assertEqual(interest, Decimal("12000.00"))
        self.assertEqual(total, Decimal("112000.00"))
        self.assertEqual(amounts[0], Decimal("9333.33"))
        self.assertEqual(amounts[-1], Decimal("9333.37"))
        self.assertEqual(sum(amounts), total)

    def test_odd_amounts_still_add_up(self):
        _, total, amounts = flat_schedule(Decimal("10000.01"), Decimal("7.77"), 7)
        self.assertEqual(sum(amounts), total)
        self.assertEqual(len(amounts), 7)

    def test_add_months_clamps_month_end(self):
        self.assertEqual(add_months(date(2026, 1, 31), 1), date(2026, 2, 28))
        self.assertEqual(add_months(date(2026, 11, 15), 3), date(2027, 2, 15))


class ApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", stdout=open("/dev/null", "w"))

    def client_for(self, username):
        client = APIClient()
        client.force_authenticate(User.objects.get(username=username))
        return client

    def loan_payload(self, **overrides):
        customer = Customer.objects.get(phone="9800000001")
        return {"customer": customer.id, "principal": "60000.00", "annual_rate": "12.00", "tenure_months": 12,
                "disbursed_on": "2026-01-31", **overrides}

    def test_admin_creates_loan_with_schedule(self):
        res = self.client_for("admin").post("/api/v1/loans/", self.loan_payload(), format="json")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data["total_payable"], "67200.00")
        self.assertEqual(res.data["outstanding"], "67200.00")
        self.assertTrue(res.data["loan_no"].startswith("LN"))
        loan = Loan.objects.get(pk=res.data["id"])
        self.assertEqual(loan.installments.count(), 12)
        self.assertEqual(loan.installments.first().due_date, date(2026, 2, 28))

    def test_agent_cannot_create_loan(self):
        res = self.client_for("agent_blr").post("/api/v1/loans/", self.loan_payload(), format="json")
        self.assertEqual(res.status_code, 403)

    def test_invalid_loan_rejected(self):
        client = self.client_for("admin")
        for bad in [{"principal": "0"}, {"tenure_months": 0}, {"annual_rate": "-1"}, {"disbursed_on": "2999-01-01"}]:
            self.assertEqual(client.post("/api/v1/loans/", self.loan_payload(**bad), format="json").status_code, 400, bad)

    def test_agent_sees_only_assigned_customers_and_loans(self):
        client = self.client_for("agent_blr")
        names = {c["name"] for c in client.get("/api/v1/customers/").data}
        self.assertEqual(names, {"Ravi Kumar", "Sunita Rao"})
        other_loan = Loan.objects.get(customer__phone="9800000003")
        self.assertEqual(client.get(f"/api/v1/loans/{other_loan.id}/").status_code, 404)

    def test_manager_sees_only_branch_loans(self):
        loans = self.client_for("manager_mum").get("/api/v1/loans/").data
        self.assertEqual({l["customer_name"] for l in loans}, {"Imran Shaikh", "Pooja Desai"})

    def test_loan_detail_has_installments(self):
        loan = Loan.objects.get(customer__phone="9800000003")
        res = self.client_for("finance").get(f"/api/v1/loans/{loan.id}/")
        self.assertEqual(len(res.data["installments"]), 6)
        self.assertEqual(res.data["amount_paid"], "0.00")

    def test_admin_creates_customer_in_agent_branch(self):
        agent = User.objects.get(username="agent_mum")
        res = self.client_for("admin").post("/api/v1/customers/", {"name": "New", "phone": "9123456789", "assigned_agent": agent.id})
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data["branch"], agent.branch_id)

    def test_customer_validation(self):
        client = self.client_for("admin")
        manager = User.objects.get(username="manager_blr")
        self.assertEqual(client.post("/api/v1/customers/", {"name": "X", "phone": "9800000001", "assigned_agent": User.objects.get(username="agent_blr").id}).status_code, 400)
        self.assertEqual(client.post("/api/v1/customers/", {"name": "X", "phone": "12345", "assigned_agent": manager.id}).status_code, 400)

    def test_agents_endpoint_admin_only(self):
        self.assertEqual(self.client_for("admin").get("/api/v1/agents/").status_code, 200)
        self.assertEqual(self.client_for("agent_blr").get("/api/v1/agents/").status_code, 403)
