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


class PostingSerializer(serializers.ModelSerializer):
    space_id = serializers.PrimaryKeyRelatedField(
        queryset=Space.objects.all(), source="space", write_only=True, required=False
    )
    space = serializers.CharField(source="space.place_name", read_only=True)
    space_address = serializers.CharField(source="space.address", read_only=True)
    place_region = serializers.CharField(source="space.place_region", read_only=True)

    posting_image = serializers.ImageField(write_only=True, required=False)
    posting_image_url = serializers.URLField(read_only=True)

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

    # ----------------------------
    # 정규화 함수 (Posting 내부)
    # ----------------------------
    def _norm_name(self, name: str) -> str:
        # 소문자, 다중 공백 축약, strip
        return " ".join(str(name).strip().split()).lower()

    def _norm_json(self, value, field="value"):
        """
        문자열/리스트/딕셔너리 모두 받아 일관된 list|dict 로 변환.
        리스트 내부 문자열은 _norm_name 적용.
        """
        import json, ast

        if value is None:
            return []

        if isinstance(value, (list, tuple)):
            return [self._norm_name(v) if isinstance(v, str) else v for v in value]

        if isinstance(value, dict):
            return value

        if isinstance(value, str):
            s = value.strip()
            if not s:
                return []
            try:
                parsed = json.loads(s)
                if isinstance(parsed, (list, tuple)):
                    return [self._norm_name(v) if isinstance(v, str) else v for v in parsed]
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass
            try:
                parsed = ast.literal_eval(s)
                if isinstance(parsed, (list, tuple)):
                    return [self._norm_name(v) if isinstance(v, str) else v for v in parsed]
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass
            # 콤마로 구분된 단일 문자열도 분해
            if "," in s:
                return [self._norm_name(x) for x in s.split(",") if x.strip()]
            return [self._norm_name(s)]

        return [value]

    # ----------------------------
    # to_internal_value (파일 deepcopy 금지 + 카테고리 정규화)
    # ----------------------------
    def to_internal_value(self, data):
        # 평평한 dict 생성 (파일 객체 deepcopy 안 함)
        payload = {k: data.get(k) for k in data.keys()} if hasattr(data, "keys") else dict(data)

        # categories 정규화
        if hasattr(data, "getlist"):  # QueryDict
            raw = data.getlist("categories")
            if len(raw) == 0:
                cats = []
            elif len(raw) == 1:
                cats = self._norm_json(raw[0], "categories")
            else:
                cats = self._norm_json(raw, "categories")
        else:
            cats = self._norm_json(payload.get("categories"), "categories")

        payload["categories"] = cats
        return super().to_internal_value(payload)

    # ----------------------------
    # 출력
    # ----------------------------
    def get_category_names(self, obj):
        return [c.name for c in obj.categories.all()]

    # ----------------------------
    # 카테고리 매핑
    # ----------------------------
    def _map_categories(self, categories_data):
        if not categories_data:
            return []

        normed_input = [self._norm_name(c) for c in categories_data]
        all_cats = Category.objects.all()
        name_map = {self._norm_name(c.name): c for c in all_cats}

        cats, missing = [], []
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
