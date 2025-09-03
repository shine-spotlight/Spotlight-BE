from django.contrib import admin
from .models import User

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'kakao_id', 'role', 'phone_number', 'created_at')
    search_fields = ('kakao_id', 'phone_number')
