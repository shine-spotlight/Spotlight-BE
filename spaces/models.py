import re
from django.db import models
from users.models import User
from categories.models import Category


class SpaceCategory(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class Space(models.Model):
    id = models.AutoField(primary_key=True)

    user = models.OneToOneField(User, on_delete=models.CASCADE)

    # 공간 기본 정보
    place_name = models.CharField(max_length=255)         # 공간명
    address = models.TextField()                          # 전체 주소 (도로명)
    postal_code = models.CharField(max_length=10, blank=True, null=True)  # ✅ 우편번호
    kakao_map_link = models.URLField(max_length=500)      # 카카오맵 URL

    category = models.ForeignKey(SpaceCategory, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField(blank=True, null=True)

    capacity_seated = models.IntegerField(blank=True, null=True)
    capacity_standing = models.IntegerField(blank=True, null=True)

    preferred_categories = models.ManyToManyField(Category, blank=True)
    is_planning_host = models.BooleanField(default=False)
    business_registration_number = models.CharField(max_length=10, unique=True)
    atmosphere = models.JSONField(default=list, blank=True)

    # ✅ 자동 저장 (프론트 입력 불가)
    place_region = models.CharField(max_length=100, blank=True, null=True, editable=False)
    place_image_url = models.URLField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # ✅ role 검증
        if self.user.role != "space":
            raise ValueError("선택한 유저는 공간 보유자 계정이 아닙니다.")

        # ✅ address에서 "시 + 구/군" 추출
        self.place_region = self.extract_region_from_address(self.address)

        super().save(*args, **kwargs)

    @staticmethod
    def extract_region_from_address(address):
        """
        주소 문자열에서 '서울시 관악구', '경남 진주시' 같은 형태로 추출
        """
        # 패턴: "OO시 OO구", "OO시 OO군", "OO도 OO시"
        match = re.search(r'([가-힣]+(시|도)\s?[가-힣]+(구|군|시))', address)
        if match:
            return match.group(1)
        return None

    @property
    def phone_number(self):
        return self.user.phone_number

    def __str__(self):
        return self.place_name
