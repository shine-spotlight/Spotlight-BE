from rest_framework import serializers
from .models import Space, SpaceCategory
from equipmentcategories.models import EquipmentCategory
from categories.models import Category

def _norm_to_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    s = str(value).strip()
    return [s] if s else []

class SpaceSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField(source="user.phone_number", read_only=True)
    category = serializers.CharField(source="category.name", read_only=True)   # 출력: 문자열
    category_name = serializers.CharField(write_only=True, required=False)      # 입력: name 문자열
    preferred_categories = serializers.ListField(
        child=serializers.CharField(), write_only=True, required=False
    )
    preferred_categories_display = serializers.SerializerMethodField(read_only=True)
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    equipments = serializers.ListField(
        child=serializers.CharField(), write_only=True, required=False
    )
    equipments_display = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Space
        fields = [
            "id", "user", "place_name", "address", "postal_code", "kakao_map_link",
            "category", "category_name", "preferred_categories", "preferred_categories_display",
            "custom_category", "description", "capacity_seated", "capacity_standing",
            "business_registration_number", "atmosphere", "place_image", "place_image_url",
            "equipments", "equipments_display", "place_region", "phone_number", "created_at",
        ]
        read_only_fields = [
            "id", "created_at", "equipments_display", "preferred_categories_display",
            "phone_number", "category", "place_region"
        ]

    def validate_atmosphere(self, value):
        return _norm_to_list(value)

    def validate(self, attrs):
        # category_name → SpaceCategory 객체로 변환
        category_name = self.initial_data.get("category_name")
        if category_name:
            try:
                category = SpaceCategory.objects.get(name=category_name)
            except SpaceCategory.DoesNotExist:
                raise serializers.ValidationError({"category_name": f"존재하지 않는 카테고리입니다: {category_name}"})
            attrs["category"] = category
        elif self.instance and not attrs.get("category"):
            attrs["category"] = self.instance.category  # 기존 값 유지

        # preferred_categories → Category 객체 리스트로 변환 (Artist와 동일)
        preferred_categories_names = self.initial_data.get("preferred_categories")
        if preferred_categories_names is not None:
            if not isinstance(preferred_categories_names, list):
                raise serializers.ValidationError({"preferred_categories": "리스트 형태여야 합니다."})
            categories = Category.objects.filter(name__in=preferred_categories_names)
            if len(categories) != len(preferred_categories_names):
                found_names = set(categories.values_list("name", flat=True))
                not_found = set(preferred_categories_names) - found_names
                raise serializers.ValidationError({"preferred_categories": f"존재하지 않는 카테고리: {', '.join(not_found)}"})
            attrs["preferred_categories"] = categories

        # 기존 값 유지 로직 (필요시)
        if self.instance:
            for field in [
                'place_name', 'address', 'postal_code', 'kakao_map_link',
                'custom_category', 'description', 'capacity_seated', 'capacity_standing',
                'business_registration_number', 'atmosphere', 'place_image', 'place_image_url'
            ]:
                if field not in attrs and hasattr(self.instance, field):
                    attrs[field] = getattr(self.instance, field)
        return attrs

    def get_equipments_display(self, obj):
        return [e.name for e in obj.equipments.all()]

    def get_preferred_categories_display(self, obj):
        return [c.name for c in obj.preferred_categories.all()]

    def create(self, validated_data):
        equipments = validated_data.pop("equipments", [])
        preferred_categories = validated_data.pop("preferred_categories", [])
        space = super().create(validated_data)
        if equipments:
            space.equipments.set(
                EquipmentCategory.objects.filter(name__in=equipments)
            )
        if preferred_categories:
            space.preferred_categories.set(preferred_categories)
        return space

    def update(self, instance, validated_data):
        equipments = validated_data.pop("equipments", None)
        preferred_categories = validated_data.pop("preferred_categories", None)
        space = super().update(instance, validated_data)
        if equipments is not None:
            space.equipments.set(
                EquipmentCategory.objects.filter(name__in=equipments)
            )
        if preferred_categories is not None:
            space.preferred_categories.set(preferred_categories)
        return space