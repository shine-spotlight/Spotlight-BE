from django.contrib import admin
from .models import Space

@admin.register(Space)
class SpaceAdmin(admin.ModelAdmin):
    list_display = ('id', 'place_name', 'category', 'user', 'created_at')
    search_fields = ('place_name', 'address', 'category')
