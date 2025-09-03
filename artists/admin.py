from django.contrib import admin
from .models import Artist

@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "name",
        "number_of_members",
        "category",
        "desired_pay",
        "is_free_allowed",
        "created_at",
    )
    search_fields = ("name", "user__kakao_id")
