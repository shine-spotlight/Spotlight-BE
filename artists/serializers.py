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
    # FK 소스 노출 예시(지침 6): 사용자 전화번호 read_only
    phone_number = serializers.CharField(source="user.phone_number", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)

    # 입력은 *_id로
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source="category",
        write_only=True,
        required=False
    )

    # 읽기용 장비 목록
    equipments = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Artist
        fields = [
            "id",
            "user",
            "name",
            "bio",
            "number_of_members",
            "category",          # read-only 용도
            "category_id",       # write-only 입력
            "custom_category",
            "category_name",
            "equipments",
            "portfolio_links",
            "profile_image",
            "profile_image_url",
            "region",
            "desired_pay",
            "is_free_allowed",
            "phone_number",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "equipments", "phone_number", "category_name"]

    # 정규화/검증
    def validate_portfolio_links(self, v): return _norm_to_list(v)
    def validate_region(self, v): return _norm_to_list(v)
    def validate_profile_image_url(self, url):
        if url and not (str(url).startswith("http://") or str(url).startswith("https://")):
            raise serializers.ValidationError("profile_image_url은 http:// 또는 https:// 이어야 합니다.")
        return url

    def get_equipments(self, obj):
        # [(id, name), ...] 형태
        return list(obj.equipments.values_list("id", "name"))
