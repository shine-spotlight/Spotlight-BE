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
    place_name = models.CharField(max_length=255)
    address = models.TextField()
    postal_code = models.CharField(max_length=10, blank=True, null=True)
    kakao_map_link = models.URLField(max_length=500)
    categories = models.ManyToManyField(SpaceCategory, blank=True, related_name="spaces")
    preferred_categories = models.ManyToManyField(Category, blank=True, related_name="preferred_spaces")
    custom_category = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    capacity_seated = models.IntegerField(blank=True, null=True)
    capacity_standing = models.IntegerField(blank=True, null=True)
    business_registration_number = models.CharField(max_length=20, unique=True)
    atmosphere = models.JSONField(default=list, blank=True)
    # 단수형 필드명 유지 (입력용, 실제 저장은 SpaceImage로)
    place_image = models.ImageField(upload_to="spaces/place/", blank=True, null=True)
    # 여러 이미지의 URL을 배열로 저장 (출력용)
    place_image_url = models.JSONField(default=list, blank=True)
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
        self.place_region = self.extract_region_from_address(self.address)
        super().save(*args, **kwargs)

    @staticmethod
    def extract_region_from_address(address: str) -> str:
        if not address:
            return None
        pattern = r'([가-힣]+(특별시|광역시|자치시|자치도|도|시)\s?[가-힣]+(시|군|구))'
        m = re.search(pattern, address)
        if m:
            return m.group(1)
        parts = address.split()
        if len(parts) >= 2:
            return f"{parts[0]} {parts[1]}"
        return parts[0] if parts else None

    @property
    def phone_number(self):
        return self.user.phone_number

    def __str__(self):
        return self.place_name

    def update_place_image_url(self):
        # 절대 URL로 변환
        urls = []
        for img in self.images.all():
            if img.image:
                if hasattr(img.image, 'url'):
                    url = img.image.url
                    if not url.startswith("http"):
                        url = settings.MEDIA_URL + url.lstrip("/")
                    # 절대 URL로 변환
                    request = getattr(self, '_request', None)
                    if request:
                        url = request.build_absolute_uri(url)
                    else:
                        # Fallback: 도메인 직접 지정 (환경에 맞게 수정)
                        url = settings.MEDIA_URL + img.image.name
                        if hasattr(settings, "SITE_DOMAIN"):
                            url = settings.SITE_DOMAIN.rstrip("/") + url
                    urls.append(url)
        self.place_image_url = urls
        self.save(update_fields=["place_image_url"])

class SpaceImage(models.Model):
    space = models.ForeignKey(Space, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to="spaces/place/")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return self.image.url if self.image else "No Image"

# signals.py (같은 파일에 둬도 무방)
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

@receiver(post_save, sender=SpaceImage)
def update_space_image_url_on_save(sender, instance, **kwargs):
    instance.space.update_place_image_url()

@receiver(post_delete, sender=SpaceImage)
def update_space_image_url_on_delete(sender, instance, **kwargs):
    instance.space.update_place_image_url()
