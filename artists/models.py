from django.db import models
from users.models import User
from categories.models import Category
from equipmentcategories.models import EquipmentCategory
from cloudinary_storage.storage import MediaCloudinaryStorage  # 추가


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
    equipments = models.ManyToManyField(
        EquipmentCategory,
        through="artistequipments.ArtistEquipment",
        blank=True,
    )

    # 프로필
    portfolio_links = models.JSONField(default=list, blank=True)
    profile_image = models.ImageField(
        upload_to="artists/profile/",
        storage=MediaCloudinaryStorage(),  # Cloudinary 스토리지 적용
        blank=True,
        null=True,
        max_length=10000
    )
    profile_image_url = models.URLField(blank=True, null=True, max_length=1000)

    # 활동 지역
    region = models.JSONField(default=list, blank=True)

    # 조건
    desired_pay = models.IntegerField(blank=True, null=True)
    is_free_allowed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def kakao_id(self):
        return getattr(self.user, "kakao_id", None)

    def save(self, *args, **kwargs):
        """
        profile_image 업로드 → profile_image_url 자동 동기화
        Cloudinary면 절대 URL, 로컬이면 /media/... 경로 저장
        """
        super().save(*args, **kwargs)

        if self.profile_image and hasattr(self.profile_image, "url"):
            url = self.profile_image.url  # Cloudinary는 절대경로 반환
            if self.profile_image_url != url:
                self.profile_image_url = url
                super().save(update_fields=["profile_image_url"])
        else:
            if self.profile_image_url:
                self.profile_image_url = ""
                super().save(update_fields=["profile_image_url"])

    def __str__(self):
        return self.name
