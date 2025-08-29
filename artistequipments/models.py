from django.db import models
from artists.models import Artist
from equipmentcategories.models import EquipmentCategory

class ArtistEquipment(models.Model):
    # 어떤 아티스트가 어떤 장비를 쓰는지 기록
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name="equipments")
    category = models.ForeignKey(EquipmentCategory, on_delete=models.SET_NULL, null=True, blank=True)
    model_description = models.TextField(blank=True)  # 예: "Shure SM58 다이나믹 마이크"

    def __str__(self):
        return f"{self.artist.name} - {self.category.name if self.category else '직접입력'}"

