from rest_framework import serializers
from django.conf import settings
from django.utils.encoding import iri_to_uri
from .models import Artist
from artistequipments.models import ArtistEquipment
from categories.models import Category
from equipmentcategories.models import EquipmentCategory
from likes.models import Like
import json
import ast

def _norm_to_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    s = str(value).strip()
    return [s] if s else []

def _norm_name(name: str) -> str:
    return "".join(str(name).strip().split()).lower()

class ArtistSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    phone_number = serializers.CharField(source="user.phone_number", read_only=True)
    categories = serializers.ListField(
        child=serializers.CharField(), write_only=True, required=False
    )
    categories_display = serializers.SerializerMethodField(read_only=True)
    equipments = serializers.ListField(
        child=serializers.CharField(), write_only=True, required=False
    )
    equipments_display = serializers.SerializerMethodField(read_only=True)
    is_liked = serializers.SerializerMethodField(read_only=True)
    artist_onboarding = serializers.SerializerMethodField(read_only=True)
    region = serializers.ListField(
        child=serializers.CharField(), required=False
    )

    class Meta:
        model = Artist
        fields = [
            "id", "user", "name", "bio", "number_of_members",
            "categories", "categories_display", "custom_category",
            "equipments", "equipments_display", "portfolio_links",
            "profile_image", "profile_image_url", "region",
            "desired_pay", "is_free_allowed", "phone_number", "created_at",
            "is_liked", "artist_onboarding"
        ]
        read_only_fields = [
            "id", "created_at", "equipments_display", "phone_number",
            "categories_display", "profile_image_url", "is_liked", "artist_onboarding"
        ]

    # ---------- helpers ----------
    def _abs_url(self, url_or_path: str | None) -> str | None:
        """상대경로/URL을 들어오든 항상 http(s) 절대 URL로 반환."""
        if not url_or_path:
            return None
        s = str(url_or_path)
        if s.startswith("http://") or s.startswith("https://"):
            return s
        request = self.context.get("request")
        if request is not None:
            # MEDIA_URL이 /media/... 같은 상대경로여도 절대 URL로 빌드됨
            return iri_to_uri(request.build_absolute_uri(s))
        base = getattr(settings, "BASE_URL", "").rstrip("/")
        if base:
            if not s.startswith("/"):
                s = "/" + s
            return iri_to_uri(base + s)
        return s  # 최후의 보루(테스트 환경)

    # ---------- field-level validators ----------
    def validate_portfolio_links(self, value):
        return _norm_to_list(value)

    def validate_region(self, value):
        if isinstance(value, str):
            value = value.strip()
            return [value] if value else []
        if isinstance(value, (list, tuple)):
            return [str(v).strip() for v in value if str(v).strip()]
        return []

    def validate_profile_image_url(self, value):
        # 읽기 전용이지만 혹시 모를 쓰기 시도를 대비: http(s)만 허용
        if value and not (str(value).startswith("http://") or str(value).startswith("https://")):
            raise serializers.ValidationError("profile_image_url은 http:// 또는 https:// 이어야 합니다.")
        return value

    # ---------- getters ----------
    def get_equipments_display(self, obj):
        return [e.name for e in obj.equipments.all()]

    def get_categories_display(self, obj):
        return [c.name for c in obj.categories.all()]

    def get_is_liked(self, obj):
        request = self.context.get("request", None)
        if request and request.user and request.user.is_authenticated:
            return Like.objects.filter(user=request.user, artist=obj).exists()
        return False

    def get_artist_onboarding(self, obj):
        required_fields = [obj.name, obj.bio, obj.region]
        if not obj.categories.all():
            return True
        return any(
            not field or (hasattr(field, "__len__") and not len(field))
            for field in required_fields
        )

    # ---------- core create/update ----------
    def create(self, validated_data):
        categories = validated_data.pop("categories", [])
        equipments = validated_data.pop("equipments", [])
        artist = super().create(validated_data)

        if categories:
            artist.categories.set(categories)
        if equipments:
            artist.equipments.set(equipments)

        # 파일 업로드가 있었다면 DB의 profile_image_url 동기화 (절대URL 저장)
        if getattr(artist, "profile_image", None):
            try:
                abs_url = self._abs_url(artist.profile_image.url)
                if abs_url and getattr(artist, "profile_image_url", None) != abs_url:
                    artist.profile_image_url = abs_url
                    artist.save(update_fields=["profile_image_url"])
            except Exception:
                # 파일 저장 직후 url 속성 접근 실패 등은 조용히 무시(응답에서 다시 계산)
                pass

        return artist

    def update(self, instance, validated_data):
        categories = validated_data.pop("categories", None)
        equipments = validated_data.pop("equipments", None)

        artist = super().update(instance, validated_data)

        if categories is not None:
            artist.categories.set(categories)
        if equipments is not None:
            artist.equipments.set(equipments)

        # 파일이 갱신되었을 수 있으니 절대URL 재계산·저장
        if getattr(artist, "profile_image", None):
            try:
                abs_url = self._abs_url(artist.profile_image.url)
                if abs_url and getattr(artist, "profile_image_url", None) != abs_url:
                    artist.profile_image_url = abs_url
                    artist.save(update_fields=["profile_image_url"])
            except Exception:
                pass

        return artist

    # ---------- request/response shaping ----------
    # ----------------------------
    # 공통 리스트 처리 함수
    # ----------------------------
    def validate_list_field(self, value, field_name):
        if value is None:
            return []
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return []
            # JSON 문자열인지 확인
            try:
                parsed = json.loads(value)
                if isinstance(parsed, (list, tuple)):
                    return [str(x).strip() for x in parsed if str(x).strip()]
            except Exception:
                pass
            # Python literal 형태인지 확인
            try:
                parsed = ast.literal_eval(value)
                if isinstance(parsed, (list, tuple)):
                    return [str(x).strip() for x in parsed if str(x).strip()]
            except Exception:
                pass
            return [value]  # 그냥 단일 값으로 fallback
        if isinstance(value, (list, tuple)):
            return [str(x).strip() for x in value if str(x).strip()]
        raise serializers.ValidationError({field_name: "리스트 형태여야 합니다."})

    # ----------------------------
    # validate 오버라이드
    # ----------------------------
    def validate(self, attrs):
        # categories
        categories_names = self.validate_list_field(self.initial_data.get("categories"), "categories")
        if categories_names:
            categories_names = [_norm_name(cat) for cat in categories_names if isinstance(cat, str)]
            categories = list(Category.objects.filter(name__in=categories_names))
            if len(categories) != len(categories_names):
                found_names = {c.name for c in categories}
                not_found = set(categories_names) - found_names
                raise serializers.ValidationError({"categories": f"존재하지 않는 카테고리: {', '.join(not_found)}"})
            attrs["categories"] = categories

        # equipments
        equipments_names = self.validate_list_field(self.initial_data.get("equipments"), "equipments")
        if equipments_names:
            equipments_names = [_norm_name(eq) for eq in equipments_names if isinstance(eq, str)]
            equipments = list(EquipmentCategory.objects.filter(name__in=equipments_names))
            if len(equipments) != len(equipments_names):
                found_names = {e.name for e in equipments}
                not_found = set(equipments_names) - found_names
                raise serializers.ValidationError({"equipments": f"존재하지 않는 장비: {', '.join(not_found)}"})
            attrs["equipments"] = equipments

        # region
        region = self.validate_list_field(self.initial_data.get("region"), "region")
        attrs["region"] = region

        # 기존 값 유지 (PATCH 대비)
        if self.instance:
            for field in [
                "name", "bio", "number_of_members", "custom_category",
                "portfolio_links", "profile_image", "profile_image_url",
                "region", "desired_pay", "is_free_allowed"
            ]:
                if field not in attrs and hasattr(self.instance, field):
                    attrs[field] = getattr(self.instance, field)

        return attrs

    def to_representation(self, obj):
        data = super().to_representation(obj)

        # 1) 업로드된 파일 우선해서 profile_image_url 보정
        file_url = None
        try:
            if getattr(obj, "profile_image", None):
                file_url = getattr(obj.profile_image, "url", None)
        except Exception:
            file_url = None

        if file_url:
            data["profile_image_url"] = self._abs_url(file_url)
        else:
            data["profile_image_url"] = self._abs_url(data.get("profile_image_url"))

        # 2) region: 리스트 → 문자열 변환
        region_list = data.get("region")
        if isinstance(region_list, list):
            data["region"] = ", ".join(region_list)

        return data
