from rest_framework import serializers
from .models import Posting
from categories.models import Category
from spaces.models import Space


class PostingSerializer(serializers.ModelSerializer):
    space_id = serializers.PrimaryKeyRelatedField(
        queryset=Space.objects.all(), source="space", write_only=True, required=False
    )
    space = serializers.CharField(source="space.place_name", read_only=True)
    category_names = serializers.ListField(
        child=serializers.CharField(), write_only=True, required=False
    )

    class Meta:
        model = Posting
        fields = [
            "id", "space", "space_id",
            "title", "description",
            "posting_image", "posting_image_url", "category_names",
            "price_type", "price_amount", "date", "created_at",
        ]
        read_only_fields = ["id", "created_at", "space", "categories"]

    def validate_posting_image_url(self, url):
        if url and not (str(url).startswith("http://") or str(url).startswith("https://")):
            raise serializers.ValidationError("posting_image_url은 http:// 또는 https:// 이어야 합니다.")
        return url

    def validate(self, attrs):
        # price 규칙
        price_type = attrs.get("price_type", getattr(self.instance, "price_type", Posting.PRICE_NEGOTIABLE))
        price_amount = attrs.get("price_amount", getattr(self.instance, "price_amount", None))
        if price_type == Posting.PRICE_PAID and price_amount is None:
            raise serializers.ValidationError(
                {"price_amount": "price_type=paid일 때 price_amount는 필수입니다."}
            )
        if price_type in (Posting.PRICE_FREE, Posting.PRICE_NEGOTIABLE):
            attrs["price_amount"] = None

        # ✅ category_names 처리 (문자열 name → FK)
        cat_names = self.initial_data.get("category_names", [])
        if cat_names:
            if not isinstance(cat_names, (list, tuple)):
                raise serializers.ValidationError({"category_names": "리스트 형식이어야 합니다."})
            categories = []
            for name in cat_names:
                try:
                    categories.append(Category.objects.get(name=name))
                except Category.DoesNotExist:
                    raise serializers.ValidationError({"category_names": f"존재하지 않는 카테고리입니다: {name}"})
            attrs["categories"] = categories

        return attrs

    def get_categories(self, obj):
        return [c.name for c in obj.categories.all()]  
