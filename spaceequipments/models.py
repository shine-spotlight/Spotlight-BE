from django.db import models
from spaces.models import Space
from equipmentcategories.models import EquipmentCategory

class SpaceEquipment(models.Model):
    # 어떤 공간이 어떤 장비를 가지고 있는지 기록
    space = models.ForeignKey(Space, on_delete=models.CASCADE, related_name="equipments")
    category = models.ForeignKey(EquipmentCategory, on_delete=models.SET_NULL, null=True, blank=True)
    model_description = models.TextField(blank=True)  # 예: "JBL EON610 스피커 2대"

    def __str__(self):
        return f"{self.space.place_name} - {self.category.name if self.category else '직접입력'}"
