from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db import transaction

from .models import Space
from .serializers import SpaceSerializer
from spaceequipments.models import SpaceEquipment
from equipmentcategories.models import EquipmentCategory

from rest_framework.exceptions import ValidationError


# 에러 포맷 통일
def bad_request(detail: str, field: str):
    return Response({"detail": detail, "code": "invalid_param", "field": field}, status=400)


def forbidden(detail: str, field: str = "space_pk"):
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
    return " ".join(str(name).strip().split()).lower()


class SpaceViewSet(viewsets.ModelViewSet):
    queryset = Space.objects.all()
    serializer_class = SpaceSerializer
    # permission_classes = [IsOwnerOrReadOnlyWithAdminPass]
    # 여기다가 추가 👇
    def perform_create(self, serializer):
        if Space.objects.filter(user=self.request.user).exists():
            raise ValidationError({"detail": "이미 공간 프로필이 있습니다.", "field": "user"})
        serializer.save(user=self.request.user)


    # 권한 가드
    def _guard_owner(self, request, space):
        if request.user.is_superuser:
            return None
        if getattr(request.user, "id", None) != space.user_id:
            return forbidden("본인만 수정 가능합니다")
        return None

    # ✅ 공간 정보 입력/수정 통합
    # POST /api/v1/spaces/info/
    @swagger_auto_schema(
        operation_summary="공간 정보 입력/수정",
        operation_description="공간 소유자가 자신의 공간 정보를 입력 또는 수정합니다.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'address': openapi.Schema(type=openapi.TYPE_STRING, description='주소'),
                'place_region': openapi.Schema(type=openapi.TYPE_STRING, description='지역'),
                'business_registration_number': openapi.Schema(type=openapi.TYPE_STRING, description='사업자 등록번호'),
                'name': openapi.Schema(type=openapi.TYPE_STRING, description='공간명'),
                'description': openapi.Schema(type=openapi.TYPE_STRING, description='설명'),
                'profile_image_url': openapi.Schema(type=openapi.TYPE_STRING, description='프로필 이미지 URL'),
                'kakao_map_link': openapi.Schema(type=openapi.TYPE_STRING, description='카카오맵 링크'),
                'place_image': openapi.Schema(type=openapi.TYPE_STRING, format='binary', description='공간 이미지'),
                'capacity_seated': openapi.Schema(type=openapi.TYPE_INTEGER, description='좌석 수'),
                'capacity_standing': openapi.Schema(type=openapi.TYPE_INTEGER, description='스탠딩 수용 인원'),
                'preferred_categories': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_INTEGER), description='선호 카테고리'),
                'equipment_category_ids': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_INTEGER), description='보유 장비 카테고리 ID 배열'),
                'custom_equipment_categories': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), description='직접입력 장비 카테고리'),
            },
        ),
        responses={200: SpaceSerializer},
        tags=["Space"]
    )
    @action(detail=False, methods=["post"], parser_classes=[MultiPartParser, FormParser, JSONParser], url_path="info")
    @transaction.atomic
    def set_info(self, request):
        try:
            space = Space.objects.get(user=request.user)
        except Space.DoesNotExist:
            return Response(
                {"detail": "공간 프로필이 없습니다."},
                status=status.HTTP_404_NOT_FOUND,
            )

        payload = {}

        # 주소
        for field in ["address", "place_region"]:
            if field in request.data:
                payload[field] = request.data.get(field)

        # 사업자 등록번호
        if "business_registration_number" in request.data:
            payload["business_registration_number"] = request.data.get("business_registration_number")

        # 상세정보 (이미지 포함)
        for field in ["name", "description", "profile_image_url", "kakao_map_link"]:
            if field in request.data:
                payload[field] = request.data.get(field)
        if "place_image" in request.FILES:
            payload["place_image"] = request.FILES["place_image"]

        # 수용 인원
        for field in ["capacity_seated", "capacity_standing"]:
            if field in request.data:
                payload[field] = request.data.get(field)

        # 선호 카테고리 (다대다)
        if "preferred_categories" in request.data:
            payload["preferred_categories"] = request.data.get("preferred_categories")

        # 보유 장비 (선택 or 직접입력)
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

            SpaceEquipment.objects.filter(space=space).delete()
            categories = EquipmentCategory.objects.filter(id__in=to_set_ids)
            SpaceEquipment.objects.bulk_create(
                [SpaceEquipment(space=space, category=cat) for cat in categories]
            )

        # 최종 저장
        ser = SpaceSerializer(space, data=payload, partial=True)
        if ser.is_valid():
            ser.save()
            return Response(ser.data, status=200)
        return bad_request(str(ser.errors), "info")

    # ✅ 필터링은 그대로 유지
    # GET /api/v1/spaces/filter/?region=서울&category=1&cap_min=50&cap_max=200
    @swagger_auto_schema(
        operation_summary="공간 필터링",
        operation_description="여러 조건(region, category, cap_min, cap_max)으로 공간을 필터링합니다.",
        manual_parameters=[
            openapi.Parameter('region', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='지역'),
            openapi.Parameter('category', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description='카테고리 ID'),
            openapi.Parameter('cap_min', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description='최소 좌석 수'),
            openapi.Parameter('cap_max', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description='최대 좌석 수'),
        ],
        responses={200: SpaceSerializer(many=True)},
        tags=["Space"]
    )
    @action(detail=False, methods=["get"], url_path="filter")
    def filter_spaces(self, request):
        qs = self.queryset
        region = request.query_params.get("region")
        category = request.query_params.get("category")
        cap_min = request.query_params.get("cap_min")
        cap_max = request.query_params.get("cap_max")

        if region:
            qs = qs.filter(place_region__icontains=region)
        if category:
            qs = qs.filter(category_id=category)
        if cap_min:
            qs = qs.filter(capacity_seated__gte=int(cap_min))
        if cap_max:
            qs = qs.filter(capacity_seated__lte=int(cap_max))

        page = self.paginate_queryset(qs.order_by("-id"))
        ser = self.get_serializer(page or qs, many=True)
        if page is not None:
            return self.get_paginated_response(ser.data)
        return Response(ser.data, status=200)
