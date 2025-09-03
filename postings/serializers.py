from rest_framework import serializers
from .models import Posting
from categories.models import Category
from spaces.models import Space

class PostingSerializer(serializers.ModelSerializer):
    space_name = serializers.CharField(source="space.place_name", read_only=True)
    categories = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Category.objects.all()
    )
    category_names = serializers.StringRelatedField(source="categories", many=True, read_only=True)

    class Meta:
        model = Posting
        fields = [
            "id",
            "space",
            "space_name",
            "title",
            "description",
            "posting_image_url",
            "categories",
            "category_names",
            "price_type",
            "price_amount",
            "date",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]
