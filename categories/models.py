from django.db import models

class Category(models.Model):
    # 공연/전시 카테고리명 (예: 밴드셋, 디제잉, 무용 등)
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name
