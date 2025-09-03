from rest_framework import serializers
from .models import Artist

class ArtistSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField(source="user.phone_number", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Artist
        fields = [
            "id",
            "user",
            "name",
            "bio",
            "number_of_members",
            "category",
            "custom_category",
            "category_name",
            "portfolio_links",
            "profile_image_url",
            "region",
            "desired_pay",
            "is_free_allowed",
            "phone_number",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]
