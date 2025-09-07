from django.contrib import admin
from .models import Suggestion


@admin.register(Suggestion)
class SuggestionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "sender_type",
        "artist",
        "space",
        "posting",
        "is_accepted",
        "created_at",
    )
    list_filter = ("sender_type", "is_accepted", "created_at")
    search_fields = ("message", "artist__name", "space__place_name")
