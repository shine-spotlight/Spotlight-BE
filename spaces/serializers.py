from rest_framework import serializers
from .models import Space, SpaceCategory
from equipmentcategories.models import EquipmentCategory
from categories.models import Category
from likes.models import Like

def _norm_to_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    s = str(value).strip()
    return [s] if s else []

class SpaceSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField(source="user.phone_number", read_only=True)
    categories = serializers.ListField(
        child=serializers.CharField(), write_only=True, required=False
    )
    categories_display = serializers.SerializerMethodField(read_only=True)
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    equipments = serializers.ListField(
        child=serializers.CharField(), write_only=True, required=False
    )
    equipments_display = serializers.SerializerMethodField(read_only=True)
    preferred_categories = serializers.ListField(
        child=serializers.CharField(), write_only=True, required=False
    )
    preferred_categories_display = serializers.SerializerMethodField(read_only=True)
    is_liked = serializers.SerializerMethodField(read_only=True)
    space_onboarding = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Space
        fields = [
            "id", "user", "place_name", "address", "postal_code", "kakao_map_link",
            "categories", "categories_display", "preferred_categories", "preferred_categories_display",
            "custom_category", "description", "capacity_seated", "capacity_standing",
            "business_registration_number", "atmosphere", "place_image", "place_image_url",
            "equipments", "equipments_display", "place_region", "phone_number", "created_at",
            "is_liked", "space_onboarding",
        ]
        read_only_fields = [
            "id", "created_at", "equipments_display", "preferred_categories_display",
            "phone_number", "categories_display", "place_region", "is_liked"
        ]

    def get_categories_display(self, obj):
        return [c.name for c in obj.categories.all()]

    def get_equipments_display(self, obj):
        return [e.name for e in obj.equipments.all()]

    def get_preferred_categories_display(self, obj):
        return [c.name for c in obj.preferred_categories.all()]

    def get_is_liked(self, obj):
        request = self.context.get("request", None)
        if request and request.user and request.user.is_authenticated:
            return Like.objects.filter(user=request.user, space=obj).exists()
        return False

    def get_space_onboarding(self, obj):
        # 필수 정보가 모두 입력되어 있으면 False, 하나라도 없으면 True
        required_fields = [
            obj.place_name,
            obj.address,
            #obj.kakao_map_link,
            obj.business_registration_number,
            obj.categories.all(),  # ManyToManyField는 all()로 체크
        ]
        return any(
            not field or (hasattr(field, "__len__") and not len(field))
            for field in required_fields
        )

    def validate_atmosphere(self, value):
        return _norm_to_list(value)

    def validate(self, attrs):
        # categories → SpaceCategory 객체 리스트로 변환
        categories_names = self.initial_data.get("categories")
        if categories_names is not None:
            if not isinstance(categories_names, list):
                raise serializers.ValidationError({"categories": "리스트 형태여야 합니다."})
            categories = SpaceCategory.objects.filter(name__in=categories_names)
            if len(categories) != len(categories_names):
                found_names = set(categories.values_list("name", flat=True))
                not_found = set(categories_names) - found_names
                raise serializers.ValidationError({"categories": f"존재하지 않는 카테고리: {', '.join(not_found)}"})
            attrs["categories"] = categories

        # preferred_categories → Category 객체 리스트로 변환 (이름 배열 허용)
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

    def create(self, validated_data):
        categories = validated_data.pop("categories", [])
        equipments = validated_data.pop("equipments", [])
        preferred_categories = validated_data.pop("preferred_categories", [])
        space = super().create(validated_data)
        if categories:
            space.categories.set(categories)
        if equipments:
            space.equipments.set(
                EquipmentCategory.objects.filter(name__in=equipments)
            )
        if preferred_categories:
            space.preferred_categories.set(preferred_categories)
        return space

    def update(self, instance, validated_data):
        categories = validated_data.pop("categories", None)
        equipments = validated_data.pop("equipments", None)
        preferred_categories = validated_data.pop("preferred_categories", None)
        space = super().update(instance, validated_data)
        if categories is not None:
            space.categories.set(categories)
        if equipments is not None:
            space.equipments.set(
                EquipmentCategory.objects.filter(name__in=equipments)
            )
        if preferred_categories is not None:
            space.preferred_categories.set(preferred_categories)
        return space