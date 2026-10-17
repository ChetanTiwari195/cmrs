from django.contrib import admin

from .models import Collection


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
