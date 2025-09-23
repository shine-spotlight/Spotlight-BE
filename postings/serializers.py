from rest_framework import serializers
from django.conf import settings
from .models import Posting
from categories.models import Category
from spaces.models import Space
from cloudinary_storage.storage import MediaCloudinaryStorage
import ast, json

storage = MediaCloudinaryStorage()


def _norm_to_list(value):
    """문자열/배열/None → 정규화된 list[str]"""
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        items = list(value)
    else:
        s = str(value).strip()
        if not s:
            return []
        try:
            parsed = json.loads(s)
            if isinstance(parsed, (list, tuple)):
                items = list(parsed)
            else:
                items = [s]
        except Exception:
            try:
                parsed = ast.literal_eval(s)
                if isinstance(parsed, (list, tuple)):
                    items = list(parsed)
                else:
                    items = [s]
            except Exception:
                items = [x for x in s.split(",") if x.strip()]
    normed, seen = [], set()
    for x in items:
        v = str(x).strip().lower()
        if v and v not in seen:
            normed.append(v)
            seen.add(v)
    return normed


def _norm_name(name: str) -> str:
    """문자열 정규화 (소문자 + 공백 정리)"""
    return "".join(str(name).strip().split()).lower()


class PostingSerializer(serializers.ModelSerializer):
    space_id = serializers.PrimaryKeyRelatedField(
        queryset=Space.objects.all(), source="space", write_only=True, required=False
    )
    space = serializers.CharField(source="space.place_name", read_only=True)
    space_address = serializers.CharField(source="space.address", read_only=True)
    place_region = serializers.CharField(source="space.place_region", read_only=True)

    # ✅ 이미지 업로드 (단일 파일)
    posting_image = serializers.ImageField(write_only=True, required=False)
    posting_image_url = serializers.URLField(read_only=True)

    # ✅ 카테고리 문자열 배열
    categories = serializers.ListField(
        child=serializers.CharField(), write_only=True, required=False
    )    
    category_names = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Posting
        fields = [
            "id", "space", "space_id",
            "space_address",
            "title", "description",
            "posting_image", "posting_image_url",
            "categories", "category_names",
            "price_type", "price_amount", "date", "created_at",
            "place_region"
        ]
        read_only_fields = [
            "id", "created_at", "space", "category_names",
            "space_address", "posting_image_url", "place_region"
        ]

    def to_internal_value(self, data):
        # QueryDict는 immutable이므로 복사본을 만들어 수정
        mutable_data = data.copy() if hasattr(data, "copy") else dict(data)
        categories = mutable_data.get("categories")
        if categories is not None:
            try:
                parsed = json.loads(categories)
                if isinstance(parsed, (list, tuple)):
                    mutable_data["categories"] = parsed
                else:
                    mutable_data["categories"] = [str(parsed)]
            except Exception:
                # fallback: 쉼표로 분리
                mutable_data["categories"] = [x for x in str(categories).split(",") if x.strip()]
        return super().to_internal_value(mutable_data)

    # ----------------------------
    # 출력
    # ----------------------------
    def get_category_names(self, obj):
        return [c.name for c in obj.categories.all()]

    # ----------------------------
    # 카테고리 매핑 유틸
    # ----------------------------
    def _map_categories(self, categories_data):
        """입력값 정규화 후 DB 이름 정규화 비교"""
        print("DEBUG: categories input =", categories_data)
        if not categories_data:
            return []

        normed_input = [_norm_name(c) for c in categories_data]

        # DB 카테고리 전부 불러와서 정규화
        all_cats = Category.objects.all()
        name_map = {_norm_name(c.name): c for c in all_cats}

        cats = []
        missing = []
        for ni in normed_input:
            if ni in name_map:
                cats.append(name_map[ni])
            else:
                missing.append(ni)

        if missing:
            raise serializers.ValidationError(
                {"categories": f"존재하지 않는 카테고리: {', '.join(missing)}"}
            )
        return cats

    # ----------------------------
    # create/update
    # ----------------------------
    def create(self, validated_data):
        validated_data.pop("posting_image", None)
        categories_data = validated_data.pop("categories", [])
        posting = super().create(validated_data)

        cats = self._map_categories(categories_data)
        posting.categories.set(cats)
        return posting

    def update(self, instance, validated_data):
        validated_data.pop("posting_image", None)
        categories_data = validated_data.pop("categories", None)

        posting = super().update(instance, validated_data)

        if categories_data is not None:
            cats = self._map_categories(categories_data)
            posting.categories.set(cats)
        return posting

    # ----------------------------
    # 가격 검증
    # ----------------------------
    def validate(self, attrs):
        price_type = attrs.get(
            "price_type", getattr(self.instance, "price_type", Posting.PRICE_NEGOTIABLE)
        )
        price_amount = attrs.get("price_amount", getattr(self.instance, "price_amount", None))

        if price_type == Posting.PRICE_PAID and price_amount is None:
            raise serializers.ValidationError(
                {"price_amount": "price_type=paid일 때 price_amount는 필수입니다."}
            )
        if price_type in (Posting.PRICE_FREE, Posting.PRICE_NEGOTIABLE):
            attrs["price_amount"] = None
        return attrs
