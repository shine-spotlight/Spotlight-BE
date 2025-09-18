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
    # 단수형 필드명 유지 (입력용, 여러 장 순차 저장)
    place_image = models.JSONField(default=list, blank=True)
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

    # def add_place_images(self, image_files, request=None):
    #     """
    #     여러 장 이미지를 순차적으로 place_image에 저장하고,
    #     각 이미지의 절대 URL을 place_image_url 배열에 append.
    #     중복 URL은 자동 제거.
    #     """
    #     url_list = self.place_image_url or []
    #     for img in image_files:
    #         self.place_image.save(img.name, img, save=True)
    #         # 절대 URL 생성
    #         url = self.place_image.url
    #         if not url.startswith("http"):
    #             if hasattr(settings, "SITE_DOMAIN"):
    #                 url = settings.SITE_DOMAIN.rstrip("/") + url
    #             else:
    #                 url = settings.MEDIA_URL + self.place_image.name
    #         if url not in url_list:
    #             url_list.append(url)
    #     # 중복 제거
    #     url_list = list(dict.fromkeys(url_list))
    #     self.place_image_url = url_list
    #     self.save(update_fields=["place_image_url"])

    def clear_place_images(self):
        """
        모든 이미지 URL을 비우고, 실제 파일도 삭제(옵션).
        """
       # self.place_image.delete(save=False)
        self.place_image_url = []
        self.save(update_fields=["place_image_url"])

# class SpaceImage(models.Model):
#     space = models.ForeignKey(Space, on_delete=models.CASCADE, related_name='images')
#     image = models.ImageField(upload_to="spaces/place/")
#     uploaded_at = models.DateTimeField(auto_now_add=True)
#     def __str__(self):
#         return self.image.url if self.image else "No Image"

# # signals.py (같은 파일에 둬도 무방)
# from django.db.models.signals import post_save, post_delete
# from django.dispatch import receiver

# @receiver(post_save, sender=SpaceImage)
# def update_space_image_url_on_save(sender, instance, **kwargs):
#     instance.space.update_place_image_url()

# @receiver(post_delete, sender=SpaceImage)
# def update_space_image_url_on_delete(sender, instance, **kwargs):
#     instance.space.update_place_image_url()
