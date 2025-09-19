from rest_framework import serializers
from .models import Space
from categories.models import Category
from likes.models import Like
from spaces.models import SpaceCategory
from equipmentcategories.models import EquipmentCategory
from django.core.files.storage import default_storage
import os
import json
import ast


def _norm_name(name: str) -> str:
    """문자열을 정규화해서 소문자 + 공백 정리"""
    return " ".join(str(name).strip().split()).lower()


class SpaceSerializer(serializers.ModelSerializer):
    # 여러 장 이미지 업로드 (입력, 파일 경로만 저장)
    place_image = serializers.ListField(
        child=serializers.ImageField(), write_only=True, required=False
    )
    # 여러 장 URL 배열 (출력, 절대 URL만 저장)
    place_image_url = serializers.ListField(
        child=serializers.URLField(max_length=1000),  # DB는 JSONField, 길이 넉넉히
        read_only=True
    )


    # 카테고리 입력/출력
    categories = serializers.ListField(child=serializers.CharField(), write_only=True, required=False)
    categories_display = serializers.SerializerMethodField(read_only=True)

    # 장비 입력/출력
    equipments = serializers.ListField(child=serializers.CharField(), write_only=True, required=False)
    equipments_display = serializers.SerializerMethodField(read_only=True)

    # 선호 카테고리 입력/출력
    preferred_categories = serializers.ListField(child=serializers.CharField(), write_only=True, required=False)
    preferred_categories_display = serializers.SerializerMethodField(read_only=True)

    # 그 외
    user = serializers.PrimaryKeyRelatedField(read_only=True)
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
            "phone_number", "categories_display", "place_image_url",
            "place_region", "is_liked"
        ]

    # ----------------------------
    # 이미지 처리
    # ----------------------------
    def create(self, validated_data):
        request = self.context.get("request")
        images = validated_data.pop("place_image", [])
        space = super().create(validated_data)

        # 업로드 파일 경로만 저장
        file_paths = []
        for img in images:
            filename = default_storage.save(os.path.join("spaces/place", img.name), img)
            file_paths.append(filename)
        space.place_image = file_paths
        space.save(update_fields=["place_image"])

        # 절대 URL 변환 및 저장 (DB는 JSONField)
        space.update_place_image_urls()
        return space

    def update(self, instance, validated_data):
        request = self.context.get("request")
        images = validated_data.pop("place_image", None)
        space = super().update(instance, validated_data)

        if images is not None:
            file_paths = []
            for img in images:
                filename = default_storage.save(os.path.join("spaces/place", img.name), img)
                file_paths.append(filename)
            space.place_image = file_paths
            space.save(update_fields=["place_image"])
            space.update_place_image_urls()

        return space

    # ----------------------------
    # 출력용 필드
    # ----------------------------
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
        return any(not field or (hasattr(field, "__len__") and not len(field)) for field in required_fields)

    # ----------------------------
    # 밸리데이션 (배열 강제)
    # ----------------------------
    def validate_list_field(self, value, field_name):
        """배열 필드를 무조건 list로 변환 (단순화)"""
        if value is None:
            return []
        if isinstance(value, str):
            value = value.strip()
            return [value] if value else []
        if isinstance(value, (list, tuple)):
            return [str(x).strip() for x in value if str(x).strip()]
        raise serializers.ValidationError({field_name: "리스트 형태여야 합니다."})

    def validate(self, attrs):
        # categories
        categories_names = self.validate_list_field(self.initial_data.get("categories"), "categories")
        if categories_names:
            categories_names = [_norm_name(cat) for cat in categories_names if isinstance(cat, str)]
            categories = list(SpaceCategory.objects.filter(name__in=categories_names))
            if len(categories) != len(categories_names):
                found_names = {c.name for c in categories}
                not_found = set(categories_names) - found_names
                raise serializers.ValidationError({"categories": f"존재하지 않는 카테고리: {', '.join(not_found)}"})
            attrs["categories"] = categories

        # preferred_categories
        preferred_names = self.validate_list_field(self.initial_data.get("preferred_categories"), "preferred_categories")
        if preferred_names:
            preferred_names = [_norm_name(cat) for cat in preferred_names if isinstance(cat, str)]
            categories = list(Category.objects.filter(name__in=preferred_names))
            if len(categories) != len(preferred_names):
                found_names = {c.name for c in categories}
                not_found = set(preferred_names) - found_names
                raise serializers.ValidationError({"preferred_categories": f"존재하지 않는 카테고리: {', '.join(not_found)}"})
            attrs["preferred_categories"] = categories

        # equipments
        equipments_names = self.validate_list_field(self.initial_data.get("equipments"), "equipments")
        if equipments_names:
            equipments_names = [_norm_name(eq) for eq in equipments_names if isinstance(eq, str)]
            equipments = list(EquipmentCategory.objects.filter(name__in=equipments_names))
            if len(equipments) != len(equipments_names):
                found_names = {e.name for e in equipments}
                not_found = set(equipments_names) - found_names
                raise serializers.ValidationError({"equipments": f"존재하지 않는 장비: {', '.join(not_found)}"})
            attrs["equipments"] = equipments

        # atmosphere
        atmosphere = self.validate_list_field(self.initial_data.get("atmosphere"), "atmosphere")
        atmosphere = [_norm_name(item) for item in atmosphere if isinstance(item, str)]
        attrs["atmosphere"] = atmosphere

        return attrs
