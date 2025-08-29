from django.db import models

class EquipmentCategory(models.Model):
    # 장비 카테고리 기본 모델
    name = models.CharField(max_length=100, unique=True)  # 예: 마이크, 스피커, 조명

    def __str__(self):
        return self.name
