from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db import transaction
from rest_framework.decorators import action
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
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    # 공간 생성 (POST)
    @swagger_auto_schema(
        operation_summary="공간 생성",
        operation_description="새로운 공간을 등록합니다. 이미 공간 프로필이 있으면 생성할 수 없습니다.",
        tags=["Space"]
    )
    def create(self, request, *args, **kwargs):
        if Space.objects.filter(user=request.user).exists():
            return bad_request("이미 공간 프로필이 있습니다.", "user")
        return super().create(request, *args, **kwargs)

    # 공간 전체 수정 (PUT)
    @swagger_auto_schema(
        operation_summary="공간 전체 수정",
        operation_description="공간 정보를 전체 수정합니다.",
        tags=["Space"]
    )
    def update(self, request, *args, **kwargs):
        space = self.get_object()
        if not (request.user.is_superuser or request.user.id == space.user_id):
            return forbidden("본인만 수정 가능합니다")
        response = super().update(request, *args, **kwargs)
        self._handle_m2m_fields(request, self.get_object())
        return response

    # 공간 부분 수정 (PATCH)
    @swagger_auto_schema(
        operation_summary="공간 부분 수정",
        operation_description="공간 정보를 일부 수정합니다.",
        tags=["Space"]
    )
    def partial_update(self, request, *args, **kwargs):
        space = self.get_object()
        if not (request.user.is_superuser or request.user.id == space.user_id):
            return forbidden("본인만 수정 가능합니다")
        response = super().partial_update(request, *args, **kwargs)
        self._handle_m2m_fields(request, self.get_object())
        return response

    # 공간 목록 조회 (GET)
    @swagger_auto_schema(
        operation_summary="공간 목록 조회",
        operation_description="모든 공간의 리스트를 조회합니다.",
        tags=["Space"]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    # 공간 상세 조회 (GET)
    @swagger_auto_schema(
        operation_summary="공간 상세 조회",
        operation_description="특정 공간의 상세 정보를 조회합니다.",
        tags=["Space"]
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    # 공간 삭제 (DELETE)
    @swagger_auto_schema(
        operation_summary="공간 삭제",
        operation_description="공간을 삭제합니다.",
        tags=["Space"]
    )
    def destroy(self, request, *args, **kwargs):
        space = self.get_object()
        if not (request.user.is_superuser or request.user.id == space.user_id):
            return forbidden("본인만 삭제 가능합니다")
        return super().destroy(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
        self._handle_m2m_fields(self.request, serializer.instance)

    def perform_update(self, serializer):
        serializer.save()
        self._handle_m2m_fields(self.request, serializer.instance)

    def _handle_m2m_fields(self, request, space):
        """
        info 액션에서 처리하던 장비/선호카테고리 등 복합 입력을 여기서 처리
        """
        # 선호 카테고리 (ManyToMany)
        if "preferred_categories" in request.data:
            preferred = request.data.get("preferred_categories")
            if isinstance(preferred, str):
                import json
                preferred = json.loads(preferred)
            space.preferred_categories.set(preferred or [])

        # 보유 장비 (선택 or 직접입력)
        ids = request.data.get("equipment_category_ids")
        customs = _norm_to_list(request.data.get("custom_equipment_categories"))
        if ids or customs:
            to_set_ids = []
            if ids:
                if not isinstance(ids, (list, tuple)):
                    raise ValidationError({"detail": "equipment_category_ids는 배열이어야 합니다", "field": "equipment_category_ids"})
                exists = list(EquipmentCategory.objects.filter(id__in=ids).values_list("id", flat=True))
                missing = set(ids) - set(exists)
                if missing:
                    raise ValidationError({"detail": f"유효하지 않은 id: {sorted(list(missing))}", "field": "equipment_category_ids"})
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

    # 공간 필터링 (커스텀)
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
    @transaction.atomic
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