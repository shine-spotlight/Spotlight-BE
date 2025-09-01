from rest_framework import serializers
from .models import Posting


class PostingSerializer(serializers.ModelSerializer):
    # 공간 이름과 주소를 자동으로 제공
    space_name = serializers.CharField(source="space.place_name", read_only=True)
    region = serializers.CharField(source="space.address", read_only=True)

    class Meta:
        model = Posting
        fields = [
            "pk",
            "space",
            "space_name",
            "region",
            "title",
            "description",
            "posting_image_url",
            "categories",
            "price_type",
            "price_amount",
            "date",
            "created_at",
        ]
