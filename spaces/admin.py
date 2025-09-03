from django.contrib import admin
from .models import Space

@admin.register(Space)
class SpaceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "place_name",
        "user",
        "category",
        "capacity_seated",
        "capacity_standing",
        "business_registration_number",
        "created_at",
    )
    search_fields = ("place_name", "user__kakao_id", "business_registration_number")
