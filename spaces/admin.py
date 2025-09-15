from django.contrib import admin
from .models import Space
from spaceequipments.models import SpaceEquipment   # ✅ 수정

@admin.register(Space)
class SpaceAdmin(admin.ModelAdmin):
    list_display = (
        "id", "place_name", "user", "get_categories_display", "custom_category",
        "capacity_seated", "capacity_standing",
        "business_registration_number", "created_at",
    )
    search_fields = ("place_name", "user__kakao_id", "business_registration_number")

    def get_categories_display(self, obj):
        return ", ".join([c.name for c in obj.categories.all()])
    get_categories_display.short_description = "카테고리"

@admin.register(SpaceEquipment)
class SpaceEquipmentAdmin(admin.ModelAdmin):
    list_display = ("id", "space", "category")
    search_fields = ("space__place_name", "category__name")
