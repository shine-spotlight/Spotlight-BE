from rest_framework import serializers
from .models import Space
from categories.models import Category
from spaceequipments.models import SpaceEquipment   # ✅ 추가

def _norm_to_list(value):
    if value is None: return []
    if isinstance(value, (list, tuple)): return list(value)
    s = str(value).strip()
    return [s] if s else []


class SpaceSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField(source="user.phone_number", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)

    # 입력은 *_id로
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source="category",
        write_only=True,
        required=False
    )

    # 읽기용 보유장비 목록
    equipments = serializers.SerializerMethodField(read_only=True)

    atmosphere = serializers.ListField(child=serializers.CharField(), required=False, default=list)

    class Meta:
        model = Space
        fields = [
            "id",
            "user",
            "place_name",
            "address",
            "postal_code",
            "kakao_map_link",
            "category",          # read-only
            "category_id",       # write-only
            "custom_category",
            "description",
            "capacity_seated",
            "capacity_standing",
            "preferred_categories",
            "is_planning_host",
            "business_registration_number",
            "atmosphere",
            "place_region",
            "place_image",
            "place_image_url",
            "equipments",
            "category_name",
            "phone_number",
            "created_at",
        ]
        read_only_fields = ["place_region", "phone_number", "created_at", "equipments", "category_name"]

    def validate_place_image_url(self, url):
        if url and not (str(url).startswith("http://") or str(url).startswith("https://")):
            raise serializers.ValidationError("place_image_url은 http:// 또는 https:// 이어야 합니다.")
        return url

    def validate_atmosphere(self, v): return _norm_to_list(v)

    def get_equipments(self, obj):
        return list(obj.equipments.values_list("id", "name"))
