import re
from django.db import models
from django.conf import settings
from users.models import User
from categories.models import Category
from equipmentcategories.models import EquipmentCategory
from cloudinary_storage.storage import MediaCloudinaryStorage


class SpaceCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Space(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    # 기본 정보
    place_name = models.CharField(max_length=255)
    address = models.TextField()
    postal_code = models.CharField(max_length=10, blank=True, null=True)
    kakao_map_link = models.URLField(max_length=500)

    # 카테고리
    categories = models.ManyToManyField(SpaceCategory, blank=True, related_name="spaces")
    preferred_categories = models.ManyToManyField(Category, blank=True, related_name="preferred_spaces")
    custom_category = models.CharField(max_length=255, blank=True, null=True)

    # 공간 설명 및 수용 인원
    description = models.TextField(blank=True, null=True)
    capacity_seated = models.IntegerField(blank=True, null=True)
    capacity_standing = models.IntegerField(blank=True, null=True)

    # 사업자 정보 및 분위기
    business_registration_number = models.CharField(max_length=20, unique=True)
    atmosphere = models.JSONField(default=list, blank=True)

    # ✅ Cloudinary 업로드 (프론트 필드명: place_image 고정)
    # 여러 장 업로드를 지원하기 위해 ImageField 자체는 단일이지만, 다중 업로드를 받으면
    # view/serializer에서 반복 저장 → JSONField에 누적 기록
    place_image = models.ImageField(
        upload_to="spaces/place/",
        storage=MediaCloudinaryStorage(),
        blank=True,
        null=True,
        max_length=10000
    )

    # 저장된 경로(public_id)와 URL 목록
    place_image_list = models.JSONField(default=list, blank=True, help_text="Cloudinary public_id 목록")
    place_image_url = models.JSONField(default=list, blank=True, help_text="Cloudinary URL 목록")

    @property
    def main_image_url(self):
        return self.place_image_url[0] if self.place_image_url else None

    equipments = models.ManyToManyField(
        EquipmentCategory,
        through="spaceequipments.SpaceEquipment",
        blank=True,
    )

    place_region = models.CharField(max_length=100, blank=True, null=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.user.role != "space":
            raise ValueError("선택한 유저는 공간 보유자 계정이 아닙니다.")

        # 주소에서 지역명 추출
        self.place_region = self.extract_region_from_address(self.address)
        super().save(*args, **kwargs)

        # ✅ Cloudinary 업로드 후 place_image_url 반영
        if self.place_image and hasattr(self.place_image, "url"):
            url = self.place_image.url
            public_id = self.place_image.name  # Cloudinary 내부 저장 key
            if url not in self.place_image_url:
                self.place_image_list.append(public_id)
                self.place_image_url.append(url)
                super().save(update_fields=["place_image_list", "place_image_url"])

    @staticmethod
    def extract_region_from_address(address: str) -> str:
        if not address:
            return None
        # "서울특별시 강남구" 같은 패턴 우선 추출
        pattern = r'([가-힣]+(특별시|광역시|자치시|자치도|도|시)\s?[가-힣]+(시|군|구))'
        m = re.search(pattern, address)
        if m:
            return m.group(1)
        # 토큰 단위로 잘라 앞 2개까지만
        parts = address.split()
        if len(parts) >= 2:
            return f"{parts[0]} {parts[1]}"
        return parts[0] if parts else None

    @property
    def phone_number(self):
        return self.user.phone_number

    def clear_place_images(self):
        """이미지 초기화"""
        self.place_image_list = []
        self.place_image_url = []
        self.save(update_fields=["place_image_list", "place_image_url"])

    def __str__(self):
        return self.place_name
