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
    place_name = models.CharField(max_length=255,null=True, blank=True)
    address = models.TextField()
    postal_code = models.CharField(max_length=10, blank=True, null=True)
    kakao_map_link = models.URLField(max_length=500, null=True, blank=True)

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

    # ✅ Cloudinary 업로드: 여러 장 지원
    place_image = models.JSONField(default=list, blank=True, help_text="Cloudinary public_id 목록")
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
            return ""

        parts = address.strip().split()
        if not parts:
            return ""

        first = parts[0]  # 도/광역시 후보
        second = parts[1] if len(parts) > 1 else ""

        # --- 도/광역시 정규화 ---
        if first.startswith("서울"):
            first = "서울특별시"
        elif first.startswith("부산"):
            first = "부산광역시"
        elif first.startswith("대구"):
            first = "대구광역시"
        elif first.startswith("인천"):
            first = "인천광역시"
        elif first.startswith("광주"):
            first = "광주광역시"
        elif first.startswith("대전"):
            first = "대전광역시"
        elif first.startswith("울산"):
            first = "울산광역시"
        elif first.startswith("세종"):
            return "세종특별자치시"
        elif first.startswith("제주"):
            first = "제주특별자치도"
        elif first.startswith("강원"):
            first = "강원특별자치도"
        elif first.startswith("경기"):
            first = "경기도"
        elif first.startswith("충북") or first.startswith("충청북"):
            first = "충청북도"
        elif first.startswith("충남") or first.startswith("충청남"):
            first = "충청남도"
        elif first.startswith("전북") or first.startswith("전라북"):
            first = "전북특별자치도"
        elif first.startswith("전남") or first.startswith("전라남"):
            first = "전라남도"
        elif first.startswith("경북") or first.startswith("경상북"):
            first = "경상북도"
        elif first.startswith("경남") or first.startswith("경상남"):
            first = "경상남도"

        # --- 저장 규칙 ---
        if second:
            # 도 단위: 시/군까지만
            if first.endswith("도") or "특별자치도" in first:
                if second.endswith("시") or second.endswith("군"):
                    return f"{first} {second}"
                return first  # 군/시 아니면 도까지만

            # 광역시/특별시: 구까지만
            if "광역시" in first or first == "서울특별시":
                if second.endswith("구"):
                    return f"{first} {second}"
                return first  # 구 아니면 광역시까지만

        return first

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
