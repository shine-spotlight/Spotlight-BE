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
