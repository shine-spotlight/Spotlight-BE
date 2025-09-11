import re
from django.db import models
from users.models import User
from categories.models import Category
from equipmentcategories.models import EquipmentCategory


class Space(models.Model):
    id = models.AutoField(primary_key=True)

    user = models.OneToOneField(User, on_delete=models.CASCADE)

    # 기본 정보
    place_name = models.CharField(max_length=255)
    address = models.TextField()
    postal_code = models.CharField(max_length=10, blank=True, null=True)
    kakao_map_link = models.URLField(max_length=500)

    # 카테고리(필수) + 커스텀 텍스트 저장
    category = models.ForeignKey(
        Category, 
        on_delete=models.PROTECT, 
        related_name="main_category_spaces"   # ✅ 수정
    )
    preferred_categories = models.ManyToManyField(
        Category, 
        blank=True, 
        related_name="preferred_spaces"       # ✅ 수정
    )
    custom_category = models.CharField(max_length=255, blank=True, null=True)

    description = models.TextField(blank=True, null=True)

    # 수용 인원
    capacity_seated = models.IntegerField(blank=True, null=True)
    capacity_standing = models.IntegerField(blank=True, null=True)

    

    #is_planning_host = models.BooleanField(default=False)
    business_registration_number = models.CharField(max_length=20, unique=True)

    # 분위기(키워드)
    atmosphere = models.JSONField(default=list, blank=True)

    # 이미지 업로드
    place_image = models.ImageField(upload_to="spaces/place/", blank=True, null=True)
    place_image_url = models.URLField(blank=True, null=True)

    # 보유 장비 (ManyToMany → spaceequipments 앱의 SpaceEquipment 사용)
    equipments = models.ManyToManyField(
        EquipmentCategory,
        through="spaceequipments.SpaceEquipment",
        blank=True,
    )

    # 주소 → 시/군/구 자동 추출 (제주특별자치도 제주시 포함)
    place_region = models.CharField(max_length=100, blank=True, null=True, editable=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.user.role != "space":
            raise ValueError("선택한 유저는 공간 보유자 계정이 아닙니다.")
        self.place_region = self.extract_region_from_address(self.address)
        super().save(*args, **kwargs)

    @staticmethod
    def extract_region_from_address(address: str) -> str:

        if not address:
            return None

    # 1. '서울시' 케이스도 허용 (특별시|광역시|자치시|자치도|도|시)
        pattern = r'([가-힣]+(특별시|광역시|자치시|자치도|도|시)\s?[가-힣]+(시|군|구))'
        m = re.search(pattern, address)
        if m:
            return m.group(1)

    # 2. fallback: 그냥 앞 두 단어 리턴
        parts = address.split()
        if len(parts) >= 2:
            return f"{parts[0]} {parts[1]}"
        return parts[0] if parts else None

    @property
    def phone_number(self):
        return self.user.phone_number

    def __str__(self):
        return self.place_name
