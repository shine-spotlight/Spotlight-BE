from rest_framework import serializers
from .models import Space, SpaceCategory


class SpaceCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SpaceCategory
        fields = ["id", "name"]


class SpaceSerializer(serializers.ModelSerializer):
    # FK: User.phone_number 읽기 전용
    phone_number = serializers.CharField(source="user.phone_number", read_only=True)
    category = SpaceCategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=SpaceCategory.objects.all(), source="category", write_only=True
    )

    class Meta:
        model = Space
        fields = [
            "id",
            "user",
            "place_name",
            "address",
            "postal_code",
            "kakao_map_link",
            "category",
            "category_id",
            "description",
            "capacity_seated",
            "capacity_standing",
            "preferred_categories",
            "is_planning_host",
            "business_registration_number",
            "atmosphere",
            "place_region",   # ✅ 자동 생성 (read_only)
            "place_image_url",
            "phone_number",
            "created_at",
        ]
        read_only_fields = ["place_region", "phone_number", "created_at"]
