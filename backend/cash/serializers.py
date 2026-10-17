from decimal import Decimal

from rest_framework import serializers

from .models import Collection


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
        return obj.agent.get_full_name() or obj.agent.username
