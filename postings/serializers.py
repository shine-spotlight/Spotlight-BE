from rest_framework import serializers
from .models import Posting
from categories.models import Category
from spaces.models import Space


class PostingSerializer(serializers.ModelSerializer):
    space_id = serializers.PrimaryKeyRelatedField(
        queryset=Space.objects.all(), source="space", write_only=True, required=False
    )
    category_ids = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source="categories", many=True, write_only=True, required=False
    )
    categories = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Posting
        fields = ["id","space","space_id","title","description",
                  "posting_image","posting_image_url","categories","category_ids",
                  "price_type","price_amount","date","created_at"]
        read_only_fields = ["id","created_at","space","categories"]

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
        return attrs

    def get_categories(self, obj):
        return [c.name for c in obj.categories.all()]  # ✅ 문자열만 반환
