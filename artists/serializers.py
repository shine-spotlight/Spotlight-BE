from rest_framework import serializers
from .models import Artist
from artistequipments.models import ArtistEquipment   # ✅ 수정
from categories.models import Category


# 단일 문자열을 배열로 정규화
def _norm_to_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    s = str(value).strip()
    return [s] if s else []


class ArtistSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField(source="user.phone_number", read_only=True)
    category = serializers.CharField(source="category.name", read_only=True)  # ✅ 문자열만 반환
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source="category",
        write_only=True,
        required=False
    )
    equipments = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Artist
        fields = [
            "id", "user", "name", "bio", "number_of_members",
            "category", "category_id", "custom_category",
            "equipments", "portfolio_links",
            "profile_image", "profile_image_url", "region",
            "desired_pay", "is_free_allowed", "phone_number", "created_at",
        ]
        read_only_fields = ["id", "created_at", "equipments", "phone_number"]

    # 정규화/검증
    def validate_portfolio_links(self, v): return _norm_to_list(v)
    def validate_region(self, v): return _norm_to_list(v)
    def validate_profile_image_url(self, url):
        if url and not (str(url).startswith("http://") or str(url).startswith("https://")):
            raise serializers.ValidationError("profile_image_url은 http:// 또는 https:// 이어야 합니다.")
        return url

    def get_equipments(self, obj):
        return [e.name for e in obj.equipments.all()]  # ✅ 문자열만 반환
