from django.contrib import admin
from .models import Suggestion

@admin.register(Suggestion)
class SuggestionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "sender",
        "receiver",
        "status",
        "is_free_allowed_suggestion",
        "is_performed_confirmed",
        "created_at",
    )
    list_filter = ("status", "is_free_allowed_suggestion", "is_performed_confirmed")
    search_fields = ("sender__kakao_id", "receiver__kakao_id", "description")
