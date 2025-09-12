from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("id",)
    list_display = (
        "id",
        "kakao_id",
        "role",
        "phone_number",
        "is_active",
        "is_staff",
        "is_superuser",
        "created_at",
    )
    list_filter = ("role", "is_staff", "is_superuser", "is_active")

    fieldsets = (
        (None, {"fields": ("kakao_id", "password")}),
        (_("개인정보"), {"fields": ("role", "phone_number")}),
        (_("권한"), {
            "fields": (
                "is_active",
                "is_staff",
                "is_superuser",
                "groups",
                "user_permissions",
            )
        }),
        (_("중요 날짜"), {"fields": ("last_login", "created_at")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "kakao_id",
                "password1",
                "password2",
                "role",
                "phone_number",
                "is_active",
                "is_staff",
                "is_superuser",
            ),
        }),
    )

    search_fields = ("kakao_id", "phone_number")
