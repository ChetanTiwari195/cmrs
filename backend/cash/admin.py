from django.contrib import admin

from .models import BankDeposit, CashSubmission, Collection, Discrepancy


class ReadOnlyAdmin(admin.ModelAdmin):
    """Money records change only through the app's services, never by hand."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Collection)
class CollectionAdmin(ReadOnlyAdmin):
    list_display = ["receipt_no", "loan", "agent", "amount", "status", "collected_at"]
    list_filter = ["status"]


@admin.register(CashSubmission)
class CashSubmissionAdmin(ReadOnlyAdmin):
    list_display = ["ref_no", "agent", "branch", "expected_amount", "received_amount", "status", "created_at"]
    list_filter = ["status", "branch"]


@admin.register(Discrepancy)
class DiscrepancyAdmin(ReadOnlyAdmin):
    list_display = ["type", "branch", "expected", "actual", "difference", "status", "created_at"]
    list_filter = ["type", "status", "branch"]


@admin.register(BankDeposit)
class BankDepositAdmin(ReadOnlyAdmin):
    list_display = ["bank_name", "reference", "branch", "amount", "deposit_date", "status", "settled_amount"]
    list_filter = ["status", "branch"]
