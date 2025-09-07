from django.db import models
from spaces.models import Space
from equipmentcategories.models import EquipmentCategory

class SpaceEquipment(models.Model):
    space = models.ForeignKey(
        "spaces.Space", 
        on_delete=models.CASCADE, 
        related_name="space_equipment_links"   # ✅ 이름 충돌 방지
    )
    category = models.ForeignKey(
        "equipmentcategories.EquipmentCategory", 
        on_delete=models.CASCADE, 
        related_name="space_equipment_links"   # ✅ 이름 충돌 방지
    )


    def __str__(self):
        return f"{self.space.place_name} - {self.category.name if self.category else '직접입력'}"
