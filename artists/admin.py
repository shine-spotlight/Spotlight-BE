from django.contrib import admin
from .models import Artist

@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    list_display = ('pk', 'name', 'user', 'desired_pay', 'created_at')  
    search_fields = ('name', 'bio')

