from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db import transaction
from .models import Space
from .serializers import SpaceSerializer
from spaceequipments.models import SpaceEquipment
from equipmentcategories.models import EquipmentCategory


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
        # 주소 등록
    # POST /api/v1/spaces/{space_pk}/address/
    @action(detail=True, methods=["post"])
    def address(self, request, pk=None):
        space = self.get_object()
        guard = self._guard_owner(request, space)
        if guard:
            return guard
        data = {
            "address": request.data.get("address"),
            "place_region": request.data.get("place_region"),
        }
        ser = SpaceSerializer(space, data=data, partial=True)
        if ser.is_valid():
            ser.save()
            return Response({
                "address": space.address,
                "place_region": space.place_region
            }, status=200)
        return bad_request(str(ser.errors), "address")

    # 사업자등록번호 등록
    # POST /api/v1/spaces/{space_pk}/business/
    @action(detail=True, methods=["post"])
    def business(self, request, pk=None):
        space = self.get_object()
        guard = self._guard_owner(request, space)
        if guard:
            return guard
        data = {
            "business_registration_number": request.data.get("business_registration_number")
        }
        ser = SpaceSerializer(space, data=data, partial=True)
        if ser.is_valid():
            ser.save()
            return Response({
                "business_registration_number": space.business_registration_number
            }, status=200)
        return bad_request(str(ser.errors), "business_registration_number")


    # 권한 가드
    def _guard_owner(self, request, space):
        if request.user.is_superuser:   # ✅ 관리자면 무조건 통과
            return None
        if getattr(request.user, "id", None) != space.user_id:
            return forbidden("본인만 수정 가능합니다")
        return None

    # 상세정보 입력 (이미지 업로드 포함)
    # POST /api/v1/spaces/{space_pk}/detail/
    @action(detail=True, methods=["post"], parser_classes=[MultiPartParser, FormParser, JSONParser], url_path="detail")
    def detail_info(self, request, pk=None):
        space = self.get_object()
        guard = self._guard_owner(request, space)
        if guard:
            return guard
        ser = SpaceSerializer(space, data=request.data, partial=True)
        if ser.is_valid():
            ser.save()
            return Response(ser.data, status=200)
        return bad_request(str(ser.errors), "detail")

    # 수용 인원
    # POST /api/v1/spaces/{space_pk}/capacity/
    @action(detail=True, methods=["post"])
    def capacity(self, request, pk=None):
        space = self.get_object()
        guard = self._guard_owner(request, space)
        if guard:
            return guard
        ser = SpaceSerializer(space, data=request.data, partial=True)
        if ser.is_valid():
            ser.save()
            return Response({
                "capacity_seated": space.capacity_seated,
                "capacity_standing": space.capacity_standing
            }, status=200)
        return bad_request(str(ser.errors), "capacity")

    # 선호 카테고리
    # POST /api/v1/spaces/{space_pk}/preference/
    @action(detail=True, methods=["post"])
    def preference(self, request, pk=None):
        space = self.get_object()
        guard = self._guard_owner(request, space)
        if guard:
            return guard
        ser = SpaceSerializer(space, data=request.data, partial=True)
        if ser.is_valid():
            ser.save()
            return Response({
                "preferred_categories": list(space.preferred_categories.values_list("id", flat=True))
            }, status=200)
        return bad_request(str(ser.errors), "preferred_categories")

    # 보유장비 (선택 or 직접입력)
    # POST /api/v1/spaces/{space_pk}/equipment/
    @action(detail=True, methods=["post"])
    @transaction.atomic
    def equipment(self, request, pk=None):
        space = self.get_object()
        guard = self._guard_owner(request, space)
        if guard:
            return guard

        ids = request.data.get("equipment_category_ids")
        customs = _norm_to_list(request.data.get("custom_equipment_categories"))

        if not ids and not customs:
            return bad_request("equipment_category_ids 또는 custom_equipment_categories 중 하나는 필요합니다", "equipment")

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

        # 연결 재설정
        SpaceEquipment.objects.filter(space=space).delete()
        categories = EquipmentCategory.objects.filter(id__in=to_set_ids)
        SpaceEquipment.objects.bulk_create(
            [SpaceEquipment(space=space, category=cat) for cat in categories]  # ✅ FK 이름 category
        )

        return Response(SpaceSerializer(space).data, status=200)

    # 필터링
    # GET /api/v1/spaces/filter/?region=서울특별시 성북구&category=1&cap_min=50&cap_max=200
    @action(detail=False, methods=["get"], url_path="filter")
    def filter_spaces(self, request):
        qs = self.queryset
        region = request.query_params.get("region")
        category = request.query_params.get("category")
        cap_min = request.query_params.get("cap_min")
        cap_max = request.query_params.get("cap_max")

        if region:
            qs = qs.filter(place_region__icontains=region)  # ✅ SQLite 대응
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
