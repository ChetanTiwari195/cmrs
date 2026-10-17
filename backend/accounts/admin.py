from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Branch, User


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ["code", "name"]
    search_fields = ["code", "name"]


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ["username", "first_name", "role", "branch", "is_active"]
    list_filter = ["role", "branch", "is_active"]
    fieldsets = BaseUserAdmin.fieldsets + (("CMRS", {"fields": ("role", "branch")}),)
    add_fieldsets = BaseUserAdmin.add_fieldsets + (("CMRS", {"fields": ("role", "branch")}),)
