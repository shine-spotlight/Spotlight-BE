from django.contrib import admin
from .models import Posting


@admin.register(Posting)
class PostingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "space",
        "get_space_address",
        "price_type",
        "price_amount",
        "date",
        "created_at",
    )
    list_filter = ("price_type", "date")
    search_fields = ("title", "space__place_name", "space__address")

    def get_space_address(self, obj):
        return obj.space.address if obj.space else "-"

    get_space_address.short_description = "공간 주소"
