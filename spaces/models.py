from django.db import models
from users.models import User
from categories.models import Category  # 공연/전시 카테고리 FK 참조

class Space(models.Model):
    # 고유 ID (자동 PK)
    id = models.AutoField(primary_key=True)

    # FK: users
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    # 공간 기본 정보
    place_name = models.CharField(max_length=255)        # 공간명
    address = models.TextField()                         # 상세 주소
    kakao_map_link = models.URLField(max_length=500)     # 카카오맵 URL
    category = models.CharField(                         # 공간 카테고리
        max_length=50,
        choices=[
            ('카페', '카페'),
            ('소극장', '소극장'),
            ('공공기관', '공공기관'),
            ('기업', '기업'),
        ]
    )
    description = models.TextField(blank=True, null=True)  # 공간 설명

    # 수용 인원
    capacity_seated = models.IntegerField(blank=True, null=True)    # 좌석 인원
    capacity_standing = models.IntegerField(blank=True, null=True)  # 스탠딩 인원

    # 공연 선호 카테고리
    preferred_categories = models.ManyToManyField(Category, blank=True)

    # 기획 공연 의사 여부
    is_planning_host = models.BooleanField(default=False)

    # 연락처 + 사업자 등록번호
    phone_number = models.CharField(max_length=20, blank=True)
    business_registration_number = models.CharField(max_length=50, blank=True)

    # 분위기 키워드
    atmosphere = models.TextField(blank=True, null=True)

    # 생성일시
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.place_name
