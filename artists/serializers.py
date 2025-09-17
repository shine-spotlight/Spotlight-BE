from rest_framework import serializers
from .models import Artist
from artistequipments.models import ArtistEquipment
from categories.models import Category
from equipmentcategories.models import EquipmentCategory
from likes.models import Like
import json
import ast

def _norm_to_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    s = str(value).strip()
    return [s] if s else []

def _norm_name(name: str) -> str:
    return " ".join(str(name).strip().split()).lower()

class ArtistSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    phone_number = serializers.CharField(source="user.phone_number", read_only=True)
    categories = serializers.ListField(
        child=serializers.CharField(), write_only=True, required=False
    )
    categories_display = serializers.SerializerMethodField(read_only=True)
    equipments = serializers.ListField(
        child=serializers.CharField(), write_only=True, required=False
    )
    equipments_display = serializers.SerializerMethodField(read_only=True)
    is_liked = serializers.SerializerMethodField(read_only=True)
    artist_onboarding = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Artist
        fields = [
            "id", "user", "name", "bio", "number_of_members",
            "categories", "categories_display", "custom_category",
            "equipments", "equipments_display", "portfolio_links",
            "profile_image",  "region",
            "desired_pay", "is_free_allowed", "phone_number", "created_at",
            "is_liked", "artist_onboarding", , "place_image_url"
        ]
        read_only_fields = [
            "id", "created_at", "equipments_display", "phone_number", "categories_display", "profile_image_url", "is_liked", "artist_onboarding"
        ]

    def validate_portfolio_links(self, value):
        return _norm_to_list(value)

    def validate_region(self, value):
        return _norm_to_list(value)

    def validate_profile_image_url(self, value):
        if value and not (str(value).startswith("http://") or str(value).startswith("https://")):
            raise serializers.ValidationError("profile_image_url은 http:// 또는 https:// 이어야 합니다.")
        return value

    def get_equipments_display(self, obj):
        return [e.name for e in obj.equipments.all()]

    def get_categories_display(self, obj):
        return [c.name for c in obj.categories.all()]

    def get_is_liked(self, obj):
        request = self.context.get("request", None)
        if request and request.user and request.user.is_authenticated:
            return Like.objects.filter(user=request.user, artist=obj).exists()
        return False

    def get_artist_onboarding(self, obj):
        required_fields = [
            obj.name,
            obj.bio,
            # obj.profile_image,
            obj.region,
        ]
        # ManyToManyField는 all()로 체크
        if not obj.categories.all():
            return True
        # if not obj.equipments.all():
        #     return True
        # 나머지 필수 필드 체크
        return any(
            not field or (hasattr(field, "__len__") and not len(field))
            for field in required_fields
        )

    def create(self, validated_data):
        categories = validated_data.pop("categories", [])
        equipments = validated_data.pop("equipments", [])
        artist = super().create(validated_data)
        if categories:
            artist.categories.set(categories)
        if equipments:
            artist.equipments.set(equipments)
        return artist

    def update(self, instance, validated_data):
        categories = validated_data.pop("categories", None)
        equipments = validated_data.pop("equipments", None)
        artist = super().update(instance, validated_data)
        if categories is not None:
            artist.categories.set(categories)
        if equipments is not None:
            artist.equipments.set(equipments)
        return artist

    def validate(self, attrs):
        # categories (공연 카테고리) - norm_name 적용
        categories_names = self.initial_data.get("categories")
        if categories_names is not None:
            if isinstance(categories_names, str):
                try:
                    categories_names = json.loads(categories_names)
                except Exception:
                    try:
                        categories_names = ast.literal_eval(categories_names)
                    except Exception:
                        raise serializers.ValidationError({"categories": "리스트 형태여야 합니다."})
            if not isinstance(categories_names, list):
                raise serializers.ValidationError({"categories": "리스트 형태여야 합니다."})
            # norm_name 적용
            categories_names = [_norm_name(cat) for cat in categories_names if isinstance(cat, str)]
            categories = list(Category.objects.filter(name__in=categories_names))
            if len(categories) != len(categories_names):
                found_names = {c.name for c in categories}
                not_found = set(categories_names) - found_names
                raise serializers.ValidationError({"categories": f"존재하지 않는 카테고리: {', '.join(not_found)}"})
            attrs["categories"] = categories

        # equipments (장비 카테고리) - norm_name 적용
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
                found_names = set([e.name for e in equipments])
                not_found = set(equipments_names) - found_names
                raise serializers.ValidationError({"equipments": f"존재하지 않는 장비: {', '.join(not_found)}"})
            attrs["equipments"] = equipments

        # region (활동 지역) - norm_name 적용
        region = self.initial_data.get("region")
        if region is not None:
            if isinstance(region, str):
                try:
                    region = json.loads(region)
                except Exception:
                    try:
                        region = ast.literal_eval(region)
                    except Exception:
                        region = [region]
            if not isinstance(region, list):
                region = [region]
            region = [_norm_name(r) for r in region if isinstance(r, str)]
            attrs["region"] = region

        # portfolio_links는 norm_name 적용하지 않음(링크이므로)

        # 기존 값 유지 로직 (필요시)
        if self.instance:
            for field in [
                'name', 'bio', 'number_of_members', 'custom_category',
                'portfolio_links', 'profile_image', 'profile_image_url',
                'region', 'desired_pay', 'is_free_allowed'
            ]:
                if field not in attrs and hasattr(self.instance, field):
                    attrs[field] = getattr(self.instance, field)
        return attrs