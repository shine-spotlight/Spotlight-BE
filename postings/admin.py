from django.contrib import admin
from .models import Posting


@admin.register(Posting)
class PostingAdmin(admin.ModelAdmin):
    list_display = (
        "pk",
        "title",
        "space",
        "date",
        "created_at",
    )
    search_fields = ("title", "description")
    list_filter = ("price_type", "date", "created_at")
