from django.contrib import admin
from .models import Like


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ("pk", "user", "target_type", "target_name", "created_at")
    search_fields = ("target_name", "user__phone_number")
