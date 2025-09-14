from rest_framework import serializers
from .models import Artist
from artistequipments.models import ArtistEquipment
from categories.models import Category
from equipmentcategories.models import EquipmentCategory

def _norm_to_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    s = str(value).strip()
    return [s] if s else []

class ArtistSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField(source="user.phone_number", read_only=True)
    category = serializers.CharField(source="category.name", read_only=True)   # 출력: 문자열
    category_name = serializers.CharField(write_only=True, required=False)      # 입력: name 문자열
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    equipments = serializers.ListField(
        child=serializers.CharField(), write_only=True, required=False
    )
    equipments_display = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Artist
        fields = [
            "id", "user", "name", "bio", "number_of_members",
            "category", "category_name", "custom_category",
            "equipments", "equipments_display", "portfolio_links",
            "profile_image", "profile_image_url", "region",
            "desired_pay", "is_free_allowed", "phone_number", "created_at",
        ]
        read_only_fields = [
            "id", "created_at", "equipments_display", "phone_number", "category"
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

    def validate(self, attrs):
        # category_name → category 객체로 변환
        category_name = self.initial_data.get("category_name")
        if category_name:
            try:
                category = Category.objects.get(name=category_name)
            except Category.DoesNotExist:
                raise serializers.ValidationError({"category_name": f"존재하지 않는 카테고리입니다: {category_name}"})
            attrs["category"] = category
        elif self.instance and not attrs.get("category"):
            attrs["category"] = self.instance.category  # 기존 값 유지

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

        def create(self, validated_data):
            validated_data.pop("category_name", None)  # ← 추가
            equipments = validated_data.pop("equipments", [])
            artist = super().create(validated_data)
            if equipments:
                artist.equipments.set(
                    EquipmentCategory.objects.filter(name__in=equipments)
            )
            return artist

    def update(self, instance, validated_data):
        validated_data.pop("category_name", None)  # ← 추가
        equipments = validated_data.pop("equipments", None)
        artist = super().update(instance, validated_data)
        if equipments is not None:
            artist.equipments.set(
                EquipmentCategory.objects.filter(name__in=equipments)
            )
        return artist