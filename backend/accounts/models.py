from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models


class Branch(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    address = models.TextField(blank=True)

    class Meta:
        ordering = ["code"]
        verbose_name_plural = "branches"

    def __str__(self):
        return f"{self.code} - {self.name}"


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        FINANCE = "FINANCE", "Finance"
        BRANCH_MANAGER = "BRANCH_MANAGER", "Branch Manager"
        AGENT = "AGENT", "Collection Agent"

    BRANCH_ROLES = (Role.BRANCH_MANAGER, Role.AGENT)

    role = models.CharField(max_length=20, choices=Role.choices)
    branch = models.ForeignKey(Branch, null=True, blank=True, on_delete=models.PROTECT, related_name="users")

    REQUIRED_FIELDS = ["email", "role"]

    def clean(self):
        super().clean()
        if self.role in self.BRANCH_ROLES and not self.branch_id:
            raise ValidationError({"branch": "Branch managers and agents must belong to a branch."})
