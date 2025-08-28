from django.contrib import admin
from .models import User

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'kakao_id', 'role', 'phone_number', 'created_at')  # 목록 화면에 표시
    readonly_fields = ('id',)  # 상세 화면에서 읽기 전용으로 표시
