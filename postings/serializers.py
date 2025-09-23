from rest_framework import serializers
from django.conf import settings
from .models import Posting
from categories.models import Category
from spaces.models import Space
import ast, json

def _norm_to_list(value):
    """문자열/배열/None → 정규화된 list[str]"""
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        items = value
    else:
        s = str(value).strip()
        if not s:
            return []
        # JSON 파싱
        try:
            parsed = json.loads(s)
            if isinstance(parsed, (list, tuple)):
                items = parsed
            else:
                items = [s]
        except Exception:
            # literal_eval
            try:
                parsed = ast.literal_eval(s)
                if isinstance(parsed, (list, tuple)):
                    items = parsed
                else:
                    items = [s]
            except Exception:
                # 쉼표 구분 문자열
                items = [x for x in s.split(",") if x.strip()]
    # 정규화: 소문자 + 공백제거 + 중복제거
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

    # ✅ 입력: 카테고리 문자열 배열
    categories = serializers.ListField(
        child=serializers.CharField(), write_only=True, required=False
    )
    category_names = serializers.SerializerMethodField(read_only=True)

    posting_image = serializers.ImageField(write_only=True, required=False)
    posting_image_url = serializers.SerializerMethodField(read_only=True)

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
    # 출력
    # ----------------------------
    def get_category_names(self, obj):
        return [c.name for c in obj.categories.all()]

    def get_posting_image_url(self, obj):
        if not obj.posting_image:
            return None
        try:
            url = obj.posting_image.url
        except Exception:
            return None

        if url.startswith("http://") or url.startswith("https://"):
            return url
        site = getattr(settings, "SITE_DOMAIN", "").rstrip("/")
        if site:
            return f"{site}/{url.lstrip('/')}"
        request = self.context.get("request")
        return request.build_absolute_uri(url) if request else url

    # ----------------------------
    # 입력 전처리
    # ----------------------------
    def to_internal_value(self, data):
        # ❌ deepcopy 유발: data.copy()
        # data = data.copy()

        # ✅ 안전하게 dict()만 사용
        mutable_data = dict(data)

        if "categories" in mutable_data:
            mutable_data["categories"] = _norm_to_list(mutable_data.get("categories"))
        return super().to_internal_value(mutable_data)

    def validate(self, attrs):
        # 가격 검증
        price_type = attrs.get("price_type", getattr(self.instance, "price_type", Posting.PRICE_NEGOTIABLE))
        price_amount = attrs.get("price_amount", getattr(self.instance, "price_amount", None))

        if price_type == Posting.PRICE_PAID and price_amount is None:
            raise serializers.ValidationError({"price_amount": "price_type=paid일 때 price_amount는 필수입니다."})
        if price_type in (Posting.PRICE_FREE, Posting.PRICE_NEGOTIABLE):
            attrs["price_amount"] = None
        return attrs

    # ----------------------------
    # 생성/수정
    # ----------------------------
    def create(self, validated_data):
        categories_data = validated_data.pop("categories", [])
        posting = super().create(validated_data)

        cats = Category.objects.filter(name__in=categories_data)
        if cats.count() != len(categories_data):
            found = {c.name for c in cats}
            missing = set(categories_data) - found
            raise serializers.ValidationError({"categories": f"존재하지 않는 카테고리: {', '.join(missing)}"})
        posting.categories.set(cats)
        return posting

    def update(self, instance, validated_data):
        categories_data = validated_data.pop("categories", None)
        posting = super().update(instance, validated_data)

        if categories_data is not None:
            cats = Category.objects.filter(name__in=categories_data)
            if cats.count() != len(categories_data):
                found = {c.name for c in cats}
                missing = set(categories_data) - found
                raise serializers.ValidationError({"categories": f"존재하지 않는 카테고리: {', '.join(missing)}"})
            posting.categories.set(cats)
        return posting
