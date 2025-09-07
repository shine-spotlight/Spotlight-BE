from django.db import models


class EquipmentCategory(models.Model):
    # 예: 마이크, 스피커, 조명
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name
