from rest_framework import serializers
from .models import SpaceEquipment
from equipmentcategories.models import EquipmentCategory


def _norm_to_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    s = str(value).strip()
    return [s] if s else []


class SpaceEquipmentSerializer(serializers.ModelSerializer):
    equipment_category = serializers.CharField(source="equipment_category.name", read_only=True)
    equipment_category_name = serializers.CharField(write_only=True, required=False)
    custom_equipment = serializers.ListField(child=serializers.CharField(), required=False)

    class Meta:
        model = SpaceEquipment
        fields = ["id", "space", "equipment_category", "equipment_category_name", "custom_equipment", "created_at"]
        read_only_fields = ["id", "created_at", "equipment_category"]

    def validate_custom_equipment(self, v):
        return _norm_to_list(v)

    def validate(self, attrs):
        cat_name = self.initial_data.get("equipment_category_name")
        if cat_name:
            try:
                category = EquipmentCategory.objects.get(name=cat_name)
            except EquipmentCategory.DoesNotExist:
                raise serializers.ValidationError(
                    {"equipment_category_name": f"존재하지 않는 장비 카테고리입니다: {cat_name}"}
                )
            attrs["equipment_category"] = category
        return attrs
