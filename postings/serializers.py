from rest_framework import serializers
from django.conf import settings
from .models import Posting
from categories.models import Category
from spaces.models import Space

def _norm_to_list(value):
    """
    입력값을 항상 배열로 보정
    - None → []
    - list/tuple → list
    - 문자열 → [문자열] 또는 파싱
    """
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        items = list(value)
    else:
        s = str(value).strip()
        # 문자열이 리스트 형태일 때 파싱
        import ast
        try:
            parsed = ast.literal_eval(s)
            if isinstance(parsed, (list, tuple)):
                items = list(parsed)
            else:
                items = [s]
        except Exception:
            # 쉼표로 구분된 문자열 처리
            if "," in s:
                items = [x for x in s.split(",")]
            else:
                items = [s] if s else []
    # 정규화: 소문자, 공백제거, 빈값제거, 중복제거
    normed = []
    seen = set()
    for x in items:
        if not isinstance(x, str):
            x = str(x)
        v = x.strip().lower()
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

    # ✅ 카테고리: 이름 기반 입력
    categories = serializers.ListField(
        child=serializers.CharField(), write_only=True, required=False
    )
    category_names = serializers.SerializerMethodField(read_only=True)

    # ✅ 이미지: 파일 업로드만 입력, URL은 자동 생성
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
        ]
        read_only_fields = ["id", "created_at", "space", "category_names", "space_address", "posting_image_url"]

    # ✅ 카테고리 이름 반환
    def get_category_names(self, obj):
        return [c.name for c in obj.categories.all()]

    # ✅ 업로드된 이미지 주소 반환
    def get_posting_image_url(self, obj):
        if obj.posting_image:
            return f"{settings.MEDIA_URL}{obj.posting_image}"
        return None

    def validate(self, attrs):
        # 가격 규칙
        price_type = attrs.get("price_type", getattr(self.instance, "price_type", Posting.PRICE_NEGOTIABLE))
        price_amount = attrs.get("price_amount", getattr(self.instance, "price_amount", None))
        if price_type == Posting.PRICE_PAID and price_amount is None:
            raise serializers.ValidationError(
                {"price_amount": "price_type=paid일 때 price_amount는 필수입니다."}
            )
        if price_type in (Posting.PRICE_FREE, Posting.PRICE_NEGOTIABLE):
            attrs["price_amount"] = None
        return attrs

    # ✅ create 시 카테고리 이름 매핑
    def create(self, validated_data):
        categories_data = _norm_to_list(validated_data.pop("categories", []))
        posting = super().create(validated_data)

        categories = []
        for name in categories_data:
            try:
                cat = Category.objects.get(name=name)
                categories.append(cat)
            except Category.DoesNotExist:
                raise serializers.ValidationError({"categories": f"존재하지 않는 카테고리: {name}"})
        if categories:
            posting.categories.set(categories)
        return posting

    # ✅ update 시 카테고리 이름 매핑 (PATCH 허용)
    def update(self, instance, validated_data):
        categories_data = validated_data.pop("categories", None)
        posting = super().update(instance, validated_data)

        if categories_data is not None:
            categories_data = _norm_to_list(categories_data)
            categories = []
            for name in categories_data:
                try:
                    cat = Category.objects.get(name=name)
                    categories.append(cat)
                except Category.DoesNotExist:
                    raise serializers.ValidationError({"categories": f"존재하지 않는 카테고리: {name}"})
            posting.categories.set(categories)
        return posting

    def to_internal_value(self, data):
        data = data.copy()
        if "categories" in data:
            data["categories"] = _norm_to_list(data["categories"])
        return super().to_internal_value(data)
