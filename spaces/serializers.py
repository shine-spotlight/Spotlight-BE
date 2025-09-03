from rest_framework import serializers
from .models import Space
from categories.models import Category

class SpaceSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField(source="user.phone_number", read_only=True)
    preferred_categories = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Category.objects.all(), required=False
    )
    preferred_category_names = serializers.StringRelatedField(
        source="preferred_categories", many=True, read_only=True
    )

    class Meta:
        model = Space
        fields = [
            "id",
            "user",
            "place_name",
            "address",
            "kakao_map_link",
            "category",
            "description",
            "capacity_seated",
            "capacity_standing",
            "preferred_categories",
            "preferred_category_names",
            "is_planning_host",
            "business_registration_number",
            "atmosphere",
            "place_region",
            "place_image_url",
            "phone_number",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "phone_number"]
