from django.contrib import admin
from .models import Space


@admin.register(Space)
class SpaceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "place_name",
        "category",
        "business_registration_number",
        "phone_number",  # ✅ User.phone_number 읽기 전용 표시
        "created_at",
    )

    # ✅ phone_number를 DB에서가 아니라 property에서 가져옴
    def phone_number(self, obj):
        return obj.user.phone_number
