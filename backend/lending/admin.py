from django.contrib import admin

from .models import Customer, Installment, Loan


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ["name", "phone", "branch", "assigned_agent"]
    list_filter = ["branch"]
    search_fields = ["name", "phone"]


class InstallmentInline(admin.TabularInline):
    model = Installment
    extra = 0
    can_delete = False
    readonly_fields = ["seq", "due_date", "amount_due", "amount_paid", "status"]


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ["loan_no", "customer", "principal", "total_payable", "status"]
    list_filter = ["status"]
    search_fields = ["customer__name", "customer__phone"]
    inlines = [InstallmentInline]

    # Loans are created through the API so the schedule is always generated.
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
