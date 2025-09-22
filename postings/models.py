from django.db import models
from django.core.exceptions import ValidationError
from users.models import User
from spaces.models import Space
from categories.models import Category
from cloudinary_storage.storage import MediaCloudinaryStorage  # ✅ Cloudinary 스토리지 추가


class Posting(models.Model):
    PRICE_PAID = "paid"
    PRICE_FREE = "free"
    PRICE_NEGOTIABLE = "negotiable"
    PRICE_TYPES = (
        (PRICE_PAID, "paid"),
        (PRICE_FREE, "free"),
        (PRICE_NEGOTIABLE, "negotiable"),
    )

    space = models.ForeignKey(Space, on_delete=models.PROTECT, related_name="postings")
    title = models.CharField(max_length=255)
    description = models.TextField()

    # 이미지 업로드 + URL 병행 (Cloudinary 저장소)
    posting_image = models.ImageField(
        upload_to="postings/",
        storage=MediaCloudinaryStorage(),  # ✅ Cloudinary 저장
        blank=True,
        null=True,
        max_length=1000,
    )
    posting_image_url = models.URLField(blank=True, null=True, max_length=1000)

    # 다중 카테고리
    categories = models.ManyToManyField(Category, blank=True, related_name="postings")

    # 가격 규칙
    price_type = models.CharField(max_length=12, choices=PRICE_TYPES, default=PRICE_NEGOTIABLE)
    price_amount = models.IntegerField(blank=True, null=True)

    # 공연 예정 날짜
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def space_address(self):
        return self.space.address if self.space else None

    def clean(self):
        # URLField 스킴 강제
        if self.posting_image_url and not (
            str(self.posting_image_url).startswith("http://")
            or str(self.posting_image_url).startswith("https://")
        ):
            raise ValidationError({"posting_image_url": "posting_image_url은 http:// 또는 https:// 이어야 합니다."})

        # 가격 규칙
        if self.price_type == self.PRICE_PAID and (self.price_amount is None):
            raise ValidationError({"price_amount": "price_type=paid일 때 price_amount는 필수입니다."})
        if self.price_type in (self.PRICE_FREE, self.PRICE_NEGOTIABLE):
            self.price_amount = None  # 저장 시 금액 무시

    def save(self, *args, **kwargs):
        # 권한/역할 가드: space.user.role 검사
        if self.space and self.space.user.role != "space":
            raise ValidationError({"space_id": "선택한 공간 소유자 계정이 올바르지 않습니다."})

        # 유효성 체크
        self.full_clean()
        super().save(*args, **kwargs)

        # ✅ posting_image_url 자동 갱신
        if self.posting_image and hasattr(self.posting_image, "url"):
            url = self.posting_image.url  # Cloudinary면 절대경로 반환됨
            if self.posting_image_url != url:
                Posting.objects.filter(pk=self.pk).update(posting_image_url=url)
        else:
            if self.posting_image_url:
                Posting.objects.filter(pk=self.pk).update(posting_image_url="")

    def __str__(self):
        return f"[{self.id}] {self.title}"
