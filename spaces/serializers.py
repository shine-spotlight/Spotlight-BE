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
    category = serializers.CharField(source="category.name", read_only=True)  # ✅ 문자열만 반환
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source="category",
        write_only=True,
        required=False
    )
    equipments = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Space
        fields = [
            "id","user","place_name","address","postal_code",
            "kakao_map_link","category","category_id","custom_category",
            "description","capacity_seated","capacity_standing",
            "preferred_categories",
            "business_registration_number","atmosphere","place_region",
            "place_image","place_image_url","equipments",
            "phone_number","created_at",
        ]
        read_only_fields = ["place_region","phone_number","created_at","equipments"]


    def validate_place_image_url(self, url):
        if url and not (str(url).startswith("http://") or str(url).startswith("https://")):
            raise serializers.ValidationError("place_image_url은 http:// 또는 https:// 이어야 합니다.")
        return url

    def validate_atmosphere(self, v): return _norm_to_list(v)

    def get_equipments(self, obj):
        return [e.name for e in obj.equipments.all()]  # ✅ 문자열만 반환
