from django.db import models


class User(models.Model):
    # 공통 회원
    kakao_id = models.CharField(max_length=255, unique=True)  # 카카오 로그인 ID
    role = models.CharField(                                # 회원 유형
        max_length=1,
        choices=[('A', 'Artist'), ('S', 'Space')]
    )
    phone_number = models.BigIntegerField(null=True, blank=True)  # 연락처 (숫자만, '-' 없이)
    created_at = models.DateTimeField(auto_now_add=True)          # 가입일

    def __str__(self):
        return f"{self.kakao_id} ({self.get_role_display()})"
