from django.utils import timezone
from rest_framework import serializers

from accounts.models import User

from .models import Customer, Installment, Loan


class CustomerSerializer(serializers.ModelSerializer):
    assigned_agent = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(role=User.Role.AGENT, is_active=True))
    agent_name = serializers.CharField(source="assigned_agent.get_full_name", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)

    class Meta:
        model = Customer
        fields = ["id", "name", "phone", "address", "assigned_agent", "agent_name", "branch", "branch_name", "created_at"]
        read_only_fields = ["branch"]


class InstallmentSerializer(serializers.ModelSerializer):
    is_overdue = serializers.SerializerMethodField()

    class Meta:
        model = Installment
        fields = ["id", "seq", "due_date", "amount_due", "amount_paid", "status", "is_overdue"]

    def get_is_overdue(self, obj):
        return obj.status != Installment.Status.PAID and obj.due_date < timezone.localdate()


class LoanSerializer(serializers.ModelSerializer):
    loan_no = serializers.ReadOnlyField()
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    amount_paid = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    outstanding = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = Loan
        fields = [
            "id", "loan_no", "customer", "customer_name", "principal", "annual_rate", "tenure_months", "disbursed_on",
            "total_interest", "total_payable", "amount_paid", "outstanding", "status", "created_at",
        ]
        read_only_fields = ["total_interest", "total_payable", "status"]

    def validate_disbursed_on(self, value):
        if value > timezone.localdate():
            raise serializers.ValidationError("Disbursement date can't be in the future.")
        return value


class LoanDetailSerializer(LoanSerializer):
    installments = InstallmentSerializer(many=True, read_only=True)

    class Meta(LoanSerializer.Meta):
        fields = LoanSerializer.Meta.fields + ["installments"]
