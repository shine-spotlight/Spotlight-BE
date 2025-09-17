from rest_framework import serializers
from .models import Space
from categories.models import Category
from likes.models import Like
from spaces.models import SpaceCategory
from equipmentcategories.models import EquipmentCategory
import json
import ast


def _norm_name(name: str) -> str:
    return " ".join(str(name).strip().split()).lower()

class SpaceImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpaceImage
        fields = ['id', 'image', 'uploaded_at']

class SpaceSerializer(serializers.ModelSerializer):
    # 입력: place_image (단수형, 여러 장 지원)
    place_image = serializers.ListField(
        child=serializers.ImageField(), write_only=True, required=False
    )
    # 출력: place_image_url (배열)
    place_image_url = serializers.ListField(read_only=True)
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
            "business_registration_number", "atmosphere", "place_image", 
            "equipments", "equipments_display", "place_region", "phone_number", "created_at",
            "is_liked", "space_onboarding", "place_image_url"
        ]
        read_only_fields = [
            "id", "created_at", "equipments_display", "preferred_categories_display",
            "phone_number", "categories_display", "place_image_url","place_region", "is_liked"
        ]

    def create(self, validated_data):
        images = validated_data.pop("place_image", [])
        categories = validated_data.pop("categories", [])
        preferred_categories = validated_data.pop("preferred_categories", [])
        space = super().create(validated_data)
        for img in images:
            SpaceImage.objects.create(space=space, image=img)
        if categories:
            space.categories.set(categories)
        if preferred_categories:
            space.preferred_categories.set(preferred_categories)
        space.update_place_image_url()
        return space

    def update(self, instance, validated_data):
        images = validated_data.pop("place_image", None)
        categories = validated_data.pop("categories", None)
        preferred_categories = validated_data.pop("preferred_categories", None)
        space = super().update(instance, validated_data)
        if images is not None:
            # 기존 이미지 삭제 후 새로 저장
            instance.images.all().delete()
            for img in images:
                SpaceImage.objects.create(space=instance, image=img)
            space.update_place_image_url()
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
        required_fields = [
            obj.place_name,
            obj.address,
            obj.business_registration_number,
            obj.categories.all(),
        ]
        return any(
            not field or (hasattr(field, "__len__") and not len(field))
            for field in required_fields
        )

    def validate_atmosphere(self, value):
        if isinstance(value, list):
            return value
        if value is None:
            return []
        return [value]

    def validate(self, attrs):
        # categories → SpaceCategory 객체 리스트로 변환 (norm_name 적용)
        categories_names = self.initial_data.get("categories")
        if categories_names is not None:
            if isinstance(categories_names, str):
                try:
                    categories_names = ast.literal_eval(categories_names)
                except Exception:
                    raise serializers.ValidationError({"categories": "리스트 형태여야 합니다."})
            if not isinstance(categories_names, list):
                raise serializers.ValidationError({"categories": "리스트 형태여야 합니다."})
            # norm_name 적용
            categories_names = [_norm_name(cat) for cat in categories_names if isinstance(cat, str)]
            categories = list(SpaceCategory.objects.filter(name__in=categories_names))
            if len(categories) != len(categories_names):
                found_names = {c.name for c in categories}
                not_found = set(categories_names) - found_names
                raise serializers.ValidationError({"categories": f"존재하지 않는 카테고리: {', '.join(not_found)}"})
            attrs["categories"] = categories

        # preferred_categories → Category 객체 리스트로 변환 (norm_name 적용)
        preferred_categories_names = self.initial_data.get("preferred_categories")
        if preferred_categories_names is not None:
            if isinstance(preferred_categories_names, str):
                try:
                    preferred_categories_names = ast.literal_eval(preferred_categories_names)
                except Exception:
                    raise serializers.ValidationError({"preferred_categories": "리스트 형태여야 합니다."})
            if not isinstance(preferred_categories_names, list):
                raise serializers.ValidationError({"preferred_categories": "리스트 형태여야 합니다."})
            preferred_categories_names = [_norm_name(cat) for cat in preferred_categories_names if isinstance(cat, str)]
            categories = list(Category.objects.filter(name__in=preferred_categories_names))
            if len(categories) != len(preferred_categories_names):
                found_names = {c.name for c in categories}
                not_found = set(preferred_categories_names) - found_names
                raise serializers.ValidationError({"preferred_categories": f"존재하지 않는 카테고리: {', '.join(not_found)}"})
            attrs["preferred_categories"] = categories

        # equipments → EquipmentCategory 객체 리스트로 변환 (norm_name 적용)
        equipments_names = self.initial_data.get("equipments")
        if equipments_names is not None:
            if isinstance(equipments_names, str):
                try:
                    equipments_names = json.loads(equipments_names)
                except Exception:
                    try:
                        equipments_names = ast.literal_eval(equipments_names)
                    except Exception:
                        raise serializers.ValidationError({"equipments": "리스트 형태여야 합니다."})
            if not isinstance(equipments_names, list):
                raise serializers.ValidationError({"equipments": "리스트 형태여야 합니다."})
            equipments_names = [_norm_name(eq) for eq in equipments_names if isinstance(eq, str)]
            equipments = list(EquipmentCategory.objects.filter(name__in=equipments_names))
            if len(equipments) != len(equipments_names):
                found_names = {e.name for e in equipments}
                not_found = set(equipments_names) - found_names
                raise serializers.ValidationError({"equipments": f"존재하지 않는 장비: {', '.join(not_found)}"})
            attrs["equipments"] = equipments

        # atmosphere → 리스트로 변환 (norm_name 적용)
        atmosphere = self.initial_data.get("atmosphere")
        if atmosphere is not None:
            if isinstance(atmosphere, str):
                try:
                    atmosphere = json.loads(atmosphere)
                except Exception:
                    try:
                        atmosphere = ast.literal_eval(atmosphere)
                    except Exception:
                        raise serializers.ValidationError({"atmosphere": "리스트 형태여야 합니다."})
            if not isinstance(atmosphere, list):
                raise serializers.ValidationError({"atmosphere": "리스트 형태여야 합니다."})
            atmosphere = [_norm_name(item) for item in atmosphere if isinstance(item, str)]
            attrs["atmosphere"] = atmosphere

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