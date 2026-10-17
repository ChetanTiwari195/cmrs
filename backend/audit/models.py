from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """Append-only record of who changed what. Rows are never updated or deleted."""

    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=50)
    entity = models.CharField(max_length=50)
    entity_id = models.CharField(max_length=50)
    before = models.JSONField(null=True, blank=True)
    after = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["entity", "entity_id"])]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError("Audit logs are append-only.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Audit logs are append-only.")


def log_action(actor, action, obj, before=None, after=None):
    return AuditLog.objects.create(
        actor=actor,
        action=action,
        entity=obj._meta.label,
        entity_id=str(obj.pk),
        before=before,
        after=after,
    )
