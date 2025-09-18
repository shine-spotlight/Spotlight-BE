from django.db import models
from django.conf import settings
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
    categories = models.ManyToManyField(Category, blank=True)
    custom_category = models.CharField(max_length=255, blank=True, null=True)

    # 필요장비 (ManyToMany → artistequipments 앱의 ArtistEquipment 사용)
    #bepo
    equipments = models.ManyToManyField(
        EquipmentCategory,
        through="artistequipments.ArtistEquipment",
        blank=True,
    )

    # 프로필11
    portfolio_links = models.JSONField(default=list, blank=True)
    profile_image = models.ImageField(upload_to="artists/profile/", blank=True, null=True, max_length=1000)
    profile_image_url = models.URLField(blank=True, null=True)

    # 활동 지역
    region = models.JSONField(default=list, blank=True)

    # 조건
    desired_pay = models.IntegerField(blank=True, null=True)
    is_free_allowed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    @property
    def kakao_id(self):
        return self.user.kakao_id if hasattr(self.user, "kakao_id") else None

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # profile_image_url 자동 갱신
        if self.profile_image and hasattr(self.profile_image, 'url'):
            # 절대 URL 생성
            url = self.profile_image.url
            if not url.startswith("http"):
                # settings에 SITE_DOMAIN이 있으면 사용, 없으면 MEDIA_URL 기준 상대경로
                site_domain = getattr(settings, "SITE_DOMAIN", None)
                if site_domain:
                    url = site_domain.rstrip("/") + url
                else:
                    url = settings.MEDIA_URL + self.profile_image.name
            if self.profile_image_url != url:
                self.profile_image_url = url
                super().save(update_fields=["profile_image_url"])
        else:
            if self.profile_image_url:
                self.profile_image_url = ""
                super().save(update_fields=["profile_image_url"])

    def __str__(self):
        return self.name
