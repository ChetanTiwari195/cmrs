from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient, APIRequestFactory

from accounts.models import Branch, User
from accounts.permissions import IsAgent, IsBranchManager
from audit.models import AuditLog, log_action


class AuthTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", stdout=open("/dev/null", "w"))

    def setUp(self):
        cache.clear()  # reset the login rate limit between tests

    def login(self, username, password="Demo@12345"):
        return self.client.post("/api/v1/auth/login/", {"username": username, "password": password})

    def test_login_success_returns_tokens(self):
        res = self.login("agent_blr")
        self.assertEqual(res.status_code, 200)
        self.assertIn("access", res.json())
        self.assertIn("refresh", res.json())

    def test_login_wrong_password(self):
        self.assertEqual(self.login("agent_blr", "wrong").status_code, 401)

    def test_login_is_rate_limited(self):
        codes = [self.login("agent_blr", "wrong").status_code for _ in range(11)]
        self.assertEqual(codes[-1], 429)

    def test_me_requires_auth(self):
        self.assertEqual(self.client.get("/api/v1/auth/me/").status_code, 401)

    def test_me_returns_role_and_branch(self):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.login('manager_blr').json()['access']}")
        data = client.get("/api/v1/auth/me/").json()
        self.assertEqual(data["role"], "BRANCH_MANAGER")
        self.assertEqual(data["branch"]["code"], "BLR01")

    def test_refresh_returns_new_access(self):
        refresh = self.login("finance").json()["refresh"]
        res = self.client.post("/api/v1/auth/refresh/", {"refresh": refresh})
        self.assertEqual(res.status_code, 200)
        self.assertIn("access", res.json())


class RoleTests(TestCase):
    def test_role_permission_blocks_wrong_role(self):
        branch = Branch.objects.create(code="T1", name="Test")
        agent = User.objects.create_user("a", password="x", role=User.Role.AGENT, branch=branch)
        request = APIRequestFactory().get("/")
        request.user = agent
        self.assertTrue(IsAgent().has_permission(request, None))
        self.assertFalse(IsBranchManager().has_permission(request, None))

    def test_agent_must_have_branch(self):
        with self.assertRaises(ValidationError):
            User(username="b", role=User.Role.AGENT).full_clean()


class AuditLogTests(TestCase):
    def test_audit_log_is_append_only(self):
        branch = Branch.objects.create(code="T1", name="Test")
        entry = log_action(None, "CREATE", branch, after={"code": "T1"})
        self.assertEqual(entry.entity, "accounts.Branch")
        with self.assertRaises(ValueError):
            entry.save()
        with self.assertRaises(ValueError):
            entry.delete()
        self.assertEqual(AuditLog.objects.count(), 1)
