from rest_framework import serializers
from .models import EquipmentCategory


class EquipmentCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = EquipmentCategory
        fields = ("id", "name")
