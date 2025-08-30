from django.db import models
from users.models import User
from categories.models import Category

class Artist(models.Model):
    # FK: users (Artist 전용)
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    # 활동 정보
    name = models.CharField(max_length=255)           # 활동명
    bio = models.TextField(blank=True, null=True)     # 소개글
    number_of_members = models.IntegerField(default=1)  # 구성원 수

    # 카테고리 (직접입력 허용: FK + custom_category)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    custom_category = models.CharField(max_length=255, blank=True, null=True)

    # 포트폴리오
    portfolio_links = models.JSONField(default=list, blank=True)  # 여러 개 가능
    profile_image_url = models.URLField(blank=True, null=True)

    # 활동 지역
    region = models.JSONField(default=list, blank=True)

    # 페이
    desired_pay = models.IntegerField(blank=True, null=True)      # 희망 페이 (만원 단위)
    is_free_allowed = models.BooleanField(default=False)          # 무료 공연 가능 여부

    created_at = models.DateTimeField(auto_now_add=True)

    # role 검증
    def save(self, *args, **kwargs):
        if self.user.role != "artist":
            raise ValueError("선택한 유저는 아티스트 계정이 아닙니다.")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
