from django.contrib import admin
from .models import Space
from spaceequipments.models import SpaceEquipment   # ✅ 수정

@admin.register(Space)
class SpaceAdmin(admin.ModelAdmin):
    list_display = (
        "id", "place_name", "user", "category", "custom_category",
        "capacity_seated", "capacity_standing",
        "business_registration_number", "created_at",
    )
    search_fields = ("place_name", "user__kakao_id", "business_registration_number")


@admin.register(SpaceEquipment)
class SpaceEquipmentAdmin(admin.ModelAdmin):
    list_display = ("id", "space", "category")
    search_fields = ("space__place_name", "equipment_category__name")
