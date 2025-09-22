import re
from django.db import models
from django.conf import settings
from users.models import User
from categories.models import Category
from equipmentcategories.models import EquipmentCategory


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

    # ✅ 이미지 (대표 이미지는 place_image_url[0] 사용)
    # 여러 장 저장 (경로 또는 Cloudinary public_id)
    place_image = models.JSONField(default=list, blank=True, help_text="Cloudinary public_id 또는 URL 목록")
    place_image_url = models.JSONField(default=list, blank=True)

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

        # 저장 후 이미지 URL 자동 갱신
        self.update_place_image_urls()

    def update_place_image_urls(self):
        """
        place_image(JSONField)에 들어있는 경로/URL을 기반으로
        place_image_url(JSONField)을 자동 세팅
        - http/https로 시작하면 그대로 사용
        - 그 외는 Cloudinary public_id로 간주하여 URL 생성
          (settings.CLOUDINARY_CLOUD_NAME가 없으면 MEDIA_URL 기반으로 보정)
        """
        cloud_name = getattr(settings, "CLOUDINARY_CLOUD_NAME", None)
        site = getattr(settings, "SITE_DOMAIN", "").rstrip("/")
        media_url = getattr(settings, "MEDIA_URL", "/media/")
        if not media_url.startswith("/"):
            media_url = "/" + media_url
        if not media_url.endswith("/"):
            media_url += "/"

        url_list = []
        for path in (self.place_image or []):
            if not path:
                continue
            s = str(path).strip()
            if not s:
                continue

            if s.startswith(("http://", "https://")):
                url_list.append(s)
            elif cloud_name:
                url_list.append(f"https://res.cloudinary.com/{cloud_name}/image/upload/{s}")
            else:
                s = s.lstrip("/")
                url_list.append(f"{site}{media_url}{s}" if site else f"{media_url}{s}")

        self.place_image_url = list(dict.fromkeys(url_list))
        super().save(update_fields=["place_image_url"])

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
        """
        모든 이미지 URL을 비우고, place_image_url도 초기화.
        (실제 파일 삭제는 선택 사항)
        """
        self.place_image = []
        self.place_image_url = []
        self.save(update_fields=["place_image", "place_image_url"])

    def __str__(self):
        return self.place_name
