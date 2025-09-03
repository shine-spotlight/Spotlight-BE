from django.contrib import admin
from .models import PointTransaction

@admin.register(PointTransaction)
class PointTransactionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "transaction_type", "amount", "created_at")
    search_fields = ("user__kakao_id", "user__phone_number")
