from rest_framework import serializers
from .models import Space
from categories.models import Category
from spaceequipments.models import SpaceEquipment

def _norm_to_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    s = str(value).strip()
    return [s] if s else []

class SpaceSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField(source="user.phone_number", read_only=True)
    user = serializers.PrimaryKeyRelatedField(read_only=True)

    # 카테고리: 출력은 name, 입력은 name 문자열
    category = serializers.CharField(source="category.name", read_only=True)
    category_name = serializers.CharField(write_only=True, required=False)

    # 선호 카테고리: 입력은 name 리스트, 출력은 name 리스트
    preferred_categories = serializers.ListField(
        child=serializers.CharField(), write_only=True, required=False
    )
    preferred_category_names = serializers.SerializerMethodField(read_only=True)

    # 장비: 출력만
    equipments = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Space
        fields = [
            "id", "user", "place_name", "address", "postal_code",
            "kakao_map_link", "category", "category_name", "custom_category",
            "description", "capacity_seated", "capacity_standing",
            "preferred_categories", "preferred_category_names",
            "business_registration_number", "atmosphere", "place_region",
            "place_image", "place_image_url", "equipments",
            "phone_number", "created_at",
        ]
        read_only_fields = [
            "place_region", "phone_number", "created_at",
            "equipments", "category", "preferred_category_names"
        ]

    def validate_place_image_url(self, url):
        if url and not (str(url).startswith("http://") or str(url).startswith("https://")):
            raise serializers.ValidationError("place_image_url은 http:// 또는 https:// 이어야 합니다.")
        return url

    def validate_atmosphere(self, v):
        return _norm_to_list(v)

    def get_equipments(self, obj):
        return [e.name for e in obj.equipments.all()]

    def get_preferred_category_names(self, obj):
        return [c.name for c in obj.preferred_categories.all()]

    def validate(self, attrs):
        # category_name 처리
        category_name = self.initial_data.get("category_name")
        if category_name:
            try:
                category = Category.objects.get(name=category_name)
            except Category.DoesNotExist:
                raise serializers.ValidationError(
                    {"category_name": f"존재하지 않는 카테고리입니다: {category_name}"}
                )
            attrs["category"] = category

        # preferred_categories 처리
        pref_names = self.initial_data.get("preferred_categories", [])
        if pref_names:
            if not isinstance(pref_names, (list, tuple)):
                raise serializers.ValidationError({"preferred_categories": "리스트 형식이어야 합니다."})
            categories = []
            for name in pref_names:
                try:
                    categories.append(Category.objects.get(name=name))
                except Category.DoesNotExist:
                    raise serializers.ValidationError(
                        {"preferred_categories": f"존재하지 않는 카테고리입니다: {name}"}
                    )
            attrs["preferred_categories"] = categories

        return attrs