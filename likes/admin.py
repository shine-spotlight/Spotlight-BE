from django.contrib import admin
from .models import Like

@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "artist", "space", "created_at")
    search_fields = ("user__phone_number", "artist__name", "space__place_name")
