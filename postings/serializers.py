from rest_framework import serializers
from django.conf import settings
from .models import Posting
from categories.models import Category
from spaces.models import Space
import ast, json


def _norm_to_list(value):
    """
    문자열/배열/None → 정규화된 list[str]
    - JSON 문자열, literal_eval, 콤마 문자열도 방어
    """
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        items = list(value)
    else:
        s = str(value).strip()
        if not s:
            return []
        # JSON 파싱
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
                # 콤마 구분 문자열
                items = [x for x in s.split(",") if x.strip()]
    # 정규화 (소문자 + 공백 제거 + 중복 제거)
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

    # ✅ 이미지 (파일 입력 / URL 출력)
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
        """업로드된 이미지 URL 반환"""
        if not obj.posting_image:
            return None
        try:
            url = obj.posting_image.url
        except Exception:
            return None
        if isinstance(url, str) and (url.startswith("http://") or url.startswith("https://")):
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
        mutable_data = dict(data)

        # title, description: 리스트로 들어오면 첫 번째 값만 사용
        for key in ["title", "description"]:
            if key in mutable_data and isinstance(mutable_data[key], (list, tuple)):
                mutable_data[key] = mutable_data[key][0]

        # price_type: 문자열 배열 방어
        if "price_type" in mutable_data:
            raw = mutable_data["price_type"]
            if isinstance(raw, (list, tuple)):
                raw = raw[0]
            if isinstance(raw, str) and raw.startswith("["):
                try:
                    parsed = ast.literal_eval(raw)
                    if isinstance(parsed, (list, tuple)) and parsed:
                        raw = parsed[0]
                except Exception:
                    pass
            mutable_data["price_type"] = str(raw).strip().lower()

        # price_amount: 문자열이면 int 캐스팅
        if "price_amount" in mutable_data:
            raw = mutable_data["price_amount"]
            if isinstance(raw, (list, tuple)):
                raw = raw[0]
            try:
                mutable_data["price_amount"] = int(raw)
            except Exception:
                mutable_data["price_amount"] = None

        # date: YYYY-MM-DD 강제
        if "date" in mutable_data:
            raw = mutable_data["date"]
            if isinstance(raw, (list, tuple)):
                raw = raw[0]
            raw = str(raw).strip()
            from datetime import datetime
            try:
                dt = datetime.strptime(raw, "%Y-%m-%d")
                mutable_data["date"] = dt.date()
            except Exception:
                pass  # 그대로 두면 DRF가 에러 리턴

        # categories: 문자열 → 리스트 보정
        if "categories" in mutable_data:
            mutable_data["categories"] = _norm_to_list(mutable_data.get("categories"))

        return super().to_internal_value(mutable_data)

    def validate(self, attrs):
        """가격 검증"""
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
