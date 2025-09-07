from django.contrib import admin
from .models import Posting


@admin.register(Posting)
class PostingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "space",
        "price_type",
        "price_amount",
        "date",
        "created_at",
    )
    list_filter = ("price_type", "date")
    search_fields = ("title", "space__place_name")
