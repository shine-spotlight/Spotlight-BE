from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db import transaction

from .models import Artist
from artistequipments.models import ArtistEquipment
from .serializers import ArtistSerializer
from equipmentcategories.models import EquipmentCategory
from users.permissions import IsOwnerOrReadOnlyWithAdminPass
from rest_framework.exceptions import ValidationError



# 에러 포맷 통일
def bad_request(detail: str, field: str):
    return Response({"detail": detail, "code": "invalid_param", "field": field}, status=400)


def forbidden(detail: str, field: str = "artist_pk"):
    return Response({"detail": detail, "code": "permission_denied", "field": field}, status=403)


# 유틸
def _norm_to_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    s = str(value).strip()
    return [s] if s else []


def _norm_name(name: str) -> str:
    # 대소문자/공백 정규화
    return " ".join(str(name).strip().split()).lower()


class ArtistViewSet(viewsets.ModelViewSet):
    queryset = Artist.objects.all()
    serializer_class = ArtistSerializer
    # permission_classes = [IsOwnerOrReadOnlyWithAdminPass]
    def perform_create(self, serializer):
        if Artist.objects.filter(user=self.request.user).exists():
            raise ValidationError({"detail": "이미 아티스트 프로필이 있습니다.", "field": "user"})
        serializer.save(user=self.request.user)

    # 권한 가드
    def _guard_owner(self, request, artist):
        if request.user.is_superuser:   # ✅ 관리자면 무조건 통과
            return None
        if getattr(request.user, "id", None) != artist.user_id:
            return forbidden("본인만 수정 가능합니다")
        return None

    # ✅ 아티스트 정보 입력/수정 통합
    # POST /api/v1/artists/info/
    @swagger_auto_schema(
        operation_summary="아티스트 정보 입력/수정",
        operation_description="아티스트가 자신의 프로필 정보를 입력 또는 수정합니다.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'name': openapi.Schema(type=openapi.TYPE_STRING, description='이름'),
                'bio': openapi.Schema(type=openapi.TYPE_STRING, description='소개'),
                'number_of_members': openapi.Schema(type=openapi.TYPE_INTEGER, description='멤버 수'),
                'category_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='카테고리 ID'),
                'custom_category': openapi.Schema(type=openapi.TYPE_STRING, description='직접입력 카테고리'),
                'region': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), description='지역'),
                'profile_image': openapi.Schema(type=openapi.TYPE_STRING, format='binary', description='프로필 이미지'),
                'profile_image_url': openapi.Schema(type=openapi.TYPE_STRING, description='프로필 이미지 URL'),
                'portfolio_links': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), description='포트폴리오 링크'),
                'desired_pay': openapi.Schema(type=openapi.TYPE_INTEGER, description='희망 페이'),
                'is_free_allowed': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='무료 허용 여부'),
                'equipment_category_ids': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_INTEGER), description='필요 장비 카테고리 ID 배열'),
                'custom_equipment_categories': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), description='직접입력 장비 카테고리'),
            },
        ),
        responses={200: ArtistSerializer},
        tags=["Artist"]
    )
    @action(detail=False, methods=["post"], parser_classes=[MultiPartParser, FormParser, JSONParser], url_path="info")
    @transaction.atomic
    def set_info(self, request):
        artist, _ = Artist.objects.get_or_create(user=request.user)
        try:
            artist = Artist.objects.get_or_create(user=request.user)
        except Artist.DoesNotExist:
            return Response(
                {"detail": "아티스트 프로필이 없습니다."},
                status=status.HTTP_404_NOT_FOUND,
            )

        payload = {}

        # 기본 정보
        for field in ["name", "bio", "number_of_members", "category_id", "custom_category"]:
            if field in request.data:
                payload[field] = request.data.get(field)

        # 지역
        if "region" in request.data:
            payload["region"] = _norm_to_list(request.data.get("region"))

        # 프로필
        if "profile_image" in request.FILES:
            payload["profile_image"] = request.FILES["profile_image"]
        if "profile_image_url" in request.data:
            payload["profile_image_url"] = request.data.get("profile_image_url")
        if "portfolio_links" in request.data:
            payload["portfolio_links"] = _norm_to_list(request.data.get("portfolio_links"))

        # 조건
        for field in ["desired_pay", "is_free_allowed"]:
            if field in request.data:
                payload[field] = request.data.get(field)

        # 필요 장비 (선택 or 직접입력)
        ids = request.data.get("equipment_category_ids")
        customs = _norm_to_list(request.data.get("custom_equipment_categories"))
        if ids or customs:
            to_set_ids = []
            if ids:
                if not isinstance(ids, (list, tuple)):
                    return bad_request("equipment_category_ids는 배열이어야 합니다", "equipment_category_ids")
                exists = list(EquipmentCategory.objects.filter(id__in=ids).values_list("id", flat=True))
                missing = set(ids) - set(exists)
                if missing:
                    return bad_request(f"유효하지 않은 id: {sorted(list(missing))}", "equipment_category_ids")
                to_set_ids.extend(exists)
            if not ids and customs:
                for name in customs:
                    norm = _norm_name(name)
                    if not norm:
                        continue
                    obj, _ = EquipmentCategory.objects.get_or_create(name=norm)
                    to_set_ids.append(obj.id)

            ArtistEquipment.objects.filter(artist=artist).delete()
            categories = EquipmentCategory.objects.filter(id__in=to_set_ids)
            ArtistEquipment.objects.bulk_create(
                [ArtistEquipment(artist=artist, category=cat) for cat in categories]
            )

        # 최종 저장
        ser = ArtistSerializer(artist, data=payload, partial=True)
        if ser.is_valid():
            ser.save()
            return Response(ser.data, status=200)
        return bad_request(str(ser.errors), "info")

    # ✅ 필터링은 그대로 유지
    # GET /api/v1/artists/filter/?region=서울&category=1&pay_min=100000&pay_max=300000
    @swagger_auto_schema(
        operation_summary="아티스트 필터링",
        operation_description="여러 조건(region, category, pay_min, pay_max)으로 아티스트를 필터링합니다.",
        manual_parameters=[
            openapi.Parameter('region', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='지역'),
            openapi.Parameter('category', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description='카테고리 ID'),
            openapi.Parameter('pay_min', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description='최소 페이'),
            openapi.Parameter('pay_max', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description='최대 페이'),
        ],
        responses={200: ArtistSerializer(many=True)},
        tags=["Artist"]
    )
    @action(detail=False, methods=["get"], url_path="filter")
    def filter_artists(self, request):
        qs = self.queryset
        region = request.query_params.get("region")
        category = request.query_params.get("category")
        pay_min = request.query_params.get("pay_min")
        pay_max = request.query_params.get("pay_max")

        if region:
            qs = qs.filter(region__icontains=region)
        if category:
            qs = qs.filter(category_id=category)
        if pay_min:
            qs = qs.filter(desired_pay__gte=int(pay_min))
        if pay_max:
            qs = qs.filter(desired_pay__lte=int(pay_max))

        page = self.paginate_queryset(qs.order_by("-id"))
        ser = self.get_serializer(page or qs, many=True)
        if page is not None:
            return self.get_paginated_response(ser.data)
        return Response(ser.data, status=200)
