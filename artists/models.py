from django.db import models
from users.models import User
from categories.models import Category
from equipmentcategories.models import EquipmentCategory


class Artist(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    # 기본 정보
    name = models.CharField(max_length=255)
    bio = models.TextField(blank=True, null=True)
    number_of_members = models.IntegerField(default=1)

    # 카테고리(필수) + 커스텀 텍스트 저장
    category = models.ForeignKey(Category, on_delete=models.PROTECT, null=False, blank=False)
    custom_category = models.CharField(max_length=255, blank=True, null=True)

    # 필요장비 (ManyToMany → artistequipments 앱의 ArtistEquipment 사용)
    equipments = models.ManyToManyField(
        EquipmentCategory,
        through="artistequipments.ArtistEquipment",
        blank=True,
    )

    # 프로필11
    portfolio_links = models.JSONField(default=list, blank=True)
    profile_image = models.ImageField(upload_to="artists/profile/", blank=True, null=True)
    profile_image_url = models.URLField(blank=True, null=True)

    # 활동 지역
    region = models.JSONField(default=list, blank=True)

    # 조건
    desired_pay = models.IntegerField(blank=True, null=True)
    is_free_allowed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.user.role != "artist":
            raise ValueError("선택한 유저는 아티스트 계정이 아닙니다.")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
