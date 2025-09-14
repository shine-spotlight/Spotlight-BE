from rest_framework import serializers
from .models import Artist
from artistequipments.models import ArtistEquipment
from categories.models import Category

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
    equipments = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Artist
        fields = [
            "id", "user", "name", "bio", "number_of_members",
            "category", "category_name", "custom_category",
            "equipments", "portfolio_links",
            "profile_image", "profile_image_url", "region",
            "desired_pay", "is_free_allowed", "phone_number", "created_at",
        ]
        read_only_fields = ["id", "created_at", "equipments", "phone_number", "category"]

    def validate_portfolio_links(self, v):
        return _norm_to_list(v)

    def validate_region(self, v):
        return _norm_to_list(v)

    def validate_profile_image_url(self, url):
        if url and not (str(url).startswith("http://") or str(url).startswith("https://")):
            raise serializers.ValidationError("profile_image_url은 http:// 또는 https:// 이어야 합니다.")
        return url

    def get_equipments(self, obj):
        return [e.name for e in obj.equipments.all()]

    def validate(self, attrs):
        category_name = self.initial_data.get("category_name")
        if category_name:
            try:
                category = Category.objects.get(name=category_name)
            except Category.DoesNotExist:
                raise serializers.ValidationError({"category_name": f"존재하지 않는 카테고리입니다: {category_name}"})
            attrs["category"] = category
        elif self.instance and not attrs.get("category"):
            attrs["category"] = self.instance.category  # 기존 값 유지
        return attrs