from django.contrib import admin
from .models import Suggestion

@admin.register(Suggestion)
class SuggestionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "sender_type",
        "artist_id",
        "space_id",
        "is_accepted",
        "is_performed_confirmed",
        "created_at",
    )
    search_fields = ("artist_id__name", "space_id__place_name")


class SuggestionAdmin(admin.ModelAdmin):
    list_display = ("id", "sender_type", "artist_id", "space_id", "is_accepted", "is_free_allowed", "is_performed_confirmed", "created_at")

    def get_fields(self, request, obj=None):
        fields = ["sender_type", "artist_id", "space_id", "message", "is_accepted", "created_at"]
        if obj:
            if obj.sender_type == "artist":
                fields.insert(5, "is_free_allowed")  # 아티스트 전용 필드
            elif obj.sender_type == "space":
                fields.insert(5, "is_performed_confirmed")  # 공간 전용 필드
        return fields

    readonly_fields = ("created_at",)