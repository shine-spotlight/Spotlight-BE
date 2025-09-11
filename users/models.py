from django.db import models

class User(models.Model):
    kakao_id = models.CharField(max_length=255, unique=True)  # 카카오 로그인 ID
    role = models.CharField(                                # 회원 유형
        max_length=10,
        choices=[('artist', 'Artist'), ('space', 'Space')],
        null=True, blank=True
    )
    # 선행 '0' 보존 + 국가코드 확장 대비
    phone_number = models.CharField(max_length=15, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)          # 가입일

    def __str__(self):
        return f"{self.kakao_id} ({self.role})"