from django.contrib import admin
from .models import Artist
from artistequipments.models import ArtistEquipment   # ✅ 수정

@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    list_display = (
        "id", "user", "name", "number_of_members",
        "get_categories", "custom_category",
        "desired_pay", "is_free_allowed", "created_at",
    )
    search_fields = ("name", "user__kakao_id")

    def get_categories(self, obj):
        return ", ".join([c.name for c in obj.categories.all()])
    get_categories.short_description = "categories"

@admin.register(ArtistEquipment)
class ArtistEquipmentAdmin(admin.ModelAdmin):
    list_display = ("id", "artist", "category")
    search_fields = ("artist__name", "equipment_category__name")
