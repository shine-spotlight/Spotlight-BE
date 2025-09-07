from django.contrib import admin
from .models import PointTransaction


@admin.register(PointTransaction)
class PointTransactionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "amount", "transaction_type", "created_at")
    list_filter = ("transaction_type", "created_at")
    search_fields = ("user__id",)
