from django.db import models

class User(models.Model):
    ROLE_CHOICES = (
        ('artist', 'Artist'),
        ('space', 'Space'),
    )
    kakao_id = models.CharField(max_length=255, unique=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    phone_number = models.BigIntegerField(null=True, blank=True)  # created_at 절대 여기 들어가면 안됨
    created_at = models.DateTimeField(auto_now_add=True)          # 따로 한 줄로 정의해야 함

    def __str__(self):
        return f"{self.role} - {self.kakao_id}"
