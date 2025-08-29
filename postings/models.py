from django.db import models
from artists.models import Artist
from categories.models import Category

class Posting(models.Model):
    # 공연 공고 작성자 (아티스트)
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE)

    # 기본 정보
    title = models.CharField(max_length=255)                # 제목
    description = models.TextField()                        # 공연 설명

    # 공연 카테고리 (여러 개 가능) → ManyToManyField
    categories = models.ManyToManyField(Category, blank=True)

    # 가격 관련
    PRICE_TYPE_CHOICES = (
        ('paid', '유료'),
        ('free', '무료'),
        ('negotiable', '협의'),
    )
    price_type = models.CharField(max_length=20, choices=PRICE_TYPE_CHOICES, default='negotiable')
    price_amount = models.IntegerField(null=True, blank=True)  # 금액 (nullable)

    # 공연 정보
    region = models.CharField(max_length=100)               # 지역
    date = models.DateField()                               # 공연 날짜
    created_at = models.DateTimeField(auto_now_add=True)    # 생성 일시

    def __str__(self):
        return f"{self.title} - {self.artist.name}"
