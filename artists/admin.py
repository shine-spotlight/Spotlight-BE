from django.contrib import admin
from .models import Artist
from artistequipments.models import ArtistEquipment   # ✅ 수정

@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    list_display = (
        "id", "user", "name", "number_of_members",
        "get_categories_display", "custom_category",
        "desired_pay", "is_free_allowed", "created_at",
    )
    search_fields = ("name", "user__kakao_id")

    def get_categories_display(self, obj):
        return ", ".join([c.name for c in obj.categories.all()])
    get_categories_display.short_description = "카테고리"

@admin.register(ArtistEquipment)
class ArtistEquipmentAdmin(admin.ModelAdmin):
    list_display = ("id", "artist", "category")
    search_fields = ("artist__name", "category__name")
