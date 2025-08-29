from django.db import models
from users.models import User
from categories.models import Category

class Artist(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)

    name = models.CharField(max_length=100)                   # 활동명
    bio = models.TextField(blank=True)                        # 소개글
    number_of_members = models.IntegerField(default=1)        # 구성원 수
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)  # 공연/전시 카테고리
    portfolio_links = models.JSONField(default=list, blank=True)  # 포트폴리오 링크
    profile_image_url = models.URLField(blank=True)           # 프로필 사진
    region = models.JSONField(default=list, blank=True)       # 활동 지역
    desired_pay = models.IntegerField(null=True, blank=True)  # 희망 페이
    is_free_allowed = models.BooleanField(default=False)      # 무료 공연 여부
    created_at = models.DateTimeField(auto_now_add=True)      # 생성일시

    @property
    def phone_number(self):
        """users 테이블에서 phone_number 끌어오기"""
        return self.user.phone_number

    def __str__(self):
        return f"{self.name} ({self.user.kakao_id})"

