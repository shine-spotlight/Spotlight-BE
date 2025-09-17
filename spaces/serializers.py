from rest_framework import serializers
from .models import Space
from categories.models import Category
from likes.models import Like
from spaces.models import SpaceCategory
from equipmentcategories.models import EquipmentCategory
import ast

class SpaceSerializer(serializers.ModelSerializer):
    categories = serializers.ListField(
        child=serializers.CharField(), write_only=True, required=False
    )
    def create(self, validated_data):
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        return super().update(instance, validated_data)
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

    def create(self, validated_data):
        categories = validated_data.pop("categories", [])
        preferred_categories = validated_data.pop("preferred_categories", [])
        space = super().create(validated_data)
        if categories:
            space.categories.set(categories)  # 객체 리스트 직접 set
        if preferred_categories:
            space.preferred_categories.set(preferred_categories)
        return space

    def update(self, instance, validated_data):
        categories = validated_data.pop("categories", None)
        preferred_categories = validated_data.pop("preferred_categories", None)
        space = super().update(instance, validated_data)
        if categories is not None:
            space.categories.set(categories)
        if preferred_categories is not None:
            space.preferred_categories.set(preferred_categories)
        return space

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
        # Ensure value is always returned as a list
        if isinstance(value, list):
            return value
        if value is None:
            return []
        return [value]

    def validate(self, attrs):
        categories_names = self.initial_data.get("categories")
        if categories_names is not None:
            # 문자열로 온 경우 파싱 시도
            if isinstance(categories_names, str):
                try:
                    categories_names = ast.literal_eval(categories_names)
                except Exception:
                    raise serializers.ValidationError({"categories": "리스트 형태여야 합니다."})
            if not isinstance(categories_names, list):
                raise serializers.ValidationError({"categories": "리스트 형태여야 합니다."})
            if not all(isinstance(cat, str) for cat in categories_names):
                raise serializers.ValidationError({"categories": "카테고리는 반드시 이름(문자열) 배열로 보내야 합니다."})
            categories = list(SpaceCategory.objects.filter(name__in=categories_names))
            if len(categories) != len(categories_names):
                found_names = {c.name for c in categories}
                not_found = set(categories_names) - found_names
                raise serializers.ValidationError({"categories": f"존재하지 않는 카테고리: {', '.join(not_found)}"})
            attrs["categories"] = categories

        # preferred_categories → Category 객체 리스트로 변환
        preferred_categories_names = self.initial_data.get("preferred_categories")
        if preferred_categories_names is not None:
            # 문자열로 온 경우 파싱 시도
            if isinstance(preferred_categories_names, str):
                try:
                    preferred_categories_names = ast.literal_eval(preferred_categories_names)
                except Exception:
                    raise serializers.ValidationError({"preferred_categories": "리스트 형태여야 합니다."})
            if not isinstance(preferred_categories_names, list):
                raise serializers.ValidationError({"preferred_categories": "리스트 형태여야 합니다."})
            if not all(isinstance(cat, str) for cat in preferred_categories_names):
                raise serializers.ValidationError({"preferred_categories": "카테고리는 반드시 이름(문자열) 배열로 보내야 합니다."})
            categories = list(Category.objects.filter(name__in=preferred_categories_names))
            if len(categories) != len(preferred_categories_names):
                found_names = {c.name for c in categories}
                not_found = set(preferred_categories_names) - found_names
                raise serializers.ValidationError({"preferred_categories": f"존재하지 않는 카테고리: {', '.join(not_found)}"})
            attrs["preferred_categories"] = categories

        # equipments → EquipmentCategory 객체 리스트로 변환
        equipments_names = self.initial_data.get("equipments")
        if equipments_names is not None:
            if not isinstance(equipments_names, list):
                raise serializers.ValidationError({"equipments": "리스트 형태여야 합니다."})
            if not all(isinstance(eq, str) for eq in equipments_names):
                raise serializers.ValidationError({"equipments": "장비는 반드시 이름(문자열) 배열로 보내야 합니다."})
            equipments = list(EquipmentCategory.objects.filter(name__in=equipments_names))
            if len(equipments) != len(equipments_names):
                found_names = set([e.name for e in equipments])
                not_found = set(equipments_names) - found_names
                raise serializers.ValidationError({"equipments": f"존재하지 않는 장비: {', '.join(not_found)}"})
            attrs["equipments"] = equipments

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