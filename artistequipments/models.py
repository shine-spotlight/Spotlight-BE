from django.db import models
from artists.models import Artist
from equipmentcategories.models import EquipmentCategory

class ArtistEquipment(models.Model):
    artist = models.ForeignKey(
        "artists.Artist", 
        on_delete=models.CASCADE, 
        related_name="artist_equipment_links"   # ✅ 이름 충돌 방지
    )
    category = models.ForeignKey(
        "equipmentcategories.EquipmentCategory", 
        on_delete=models.CASCADE, 
        related_name="artist_equipment_links"   # ✅ 이름 충돌 방지
    )


    def __str__(self):
        return f"{self.artist.name} - {self.category.name if self.category else '직접입력'}"

