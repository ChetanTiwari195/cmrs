from decimal import Decimal

from rest_framework import serializers

from .models import CashSubmission, Collection, Discrepancy


class CollectionSerializer(serializers.ModelSerializer):
    receipt_no = serializers.ReadOnlyField()
    loan_no = serializers.ReadOnlyField(source="loan.loan_no")
    customer_name = serializers.ReadOnlyField(source="loan.customer.name")
    agent_name = serializers.SerializerMethodField()
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"))

    class Meta:
        model = Collection
        fields = ["id", "receipt_no", "loan", "loan_no", "customer_name", "agent", "agent_name", "amount", "collected_at", "status", "idempotency_key"]
        read_only_fields = ["agent", "collected_at", "status"]
        extra_kwargs = {"idempotency_key": {"write_only": True, "validators": []}}

    def get_agent_name(self, obj):
        return display_name(obj.agent)


def display_name(user):
    return (user.get_full_name() or user.username) if user else None


class CashSubmissionSerializer(serializers.ModelSerializer):
    ref_no = serializers.ReadOnlyField()
    agent_name = serializers.SerializerMethodField()
    reviewed_by_name = serializers.SerializerMethodField()
    branch_name = serializers.ReadOnlyField(source="branch.name")
    collection_count = serializers.IntegerField(read_only=True)
    difference = serializers.SerializerMethodField()

    class Meta:
        model = CashSubmission
        fields = [
            "id", "ref_no", "agent", "agent_name", "branch", "branch_name", "collection_count", "expected_amount",
            "received_amount", "difference", "status", "remarks", "reviewed_by_name", "reviewed_at", "created_at",
        ]

    def get_agent_name(self, obj):
        return display_name(obj.agent)

    def get_reviewed_by_name(self, obj):
        return display_name(obj.reviewed_by)

    def get_difference(self, obj):
        return None if obj.received_amount is None else str(obj.expected_amount - obj.received_amount)


class ApproveSerializer(serializers.Serializer):
    received_amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0"))
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class RemarksSerializer(serializers.Serializer):
    remarks = serializers.CharField(allow_blank=True)


class DiscrepancySerializer(serializers.ModelSerializer):
    branch_name = serializers.ReadOnlyField(source="branch.name")
    reference = serializers.SerializerMethodField()
    resolved_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Discrepancy
        fields = [
            "id", "type", "branch", "branch_name", "reference", "expected", "actual", "difference", "note",
            "status", "resolution_note", "resolved_by_name", "resolved_at", "created_at",
        ]

    def get_reference(self, obj):
        return obj.submission.ref_no if obj.submission_id else None

    def get_resolved_by_name(self, obj):
        return display_name(obj.resolved_by)


class ResolveSerializer(serializers.Serializer):
    resolution_note = serializers.CharField(allow_blank=True)
