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

    # 권한 가드
    def _guard_owner(self, request, artist):
        if request.user.is_superuser:   # ✅ 관리자면 무조건 통과
            return None
        if getattr(request.user, "id", None) != artist.user_id:
            return forbidden("본인만 수정 가능합니다")
        return None

    # ✅ 아티스트 정보 입력/수정 통합
    # POST /api/v1/artists/info/
    @action(detail=False, methods=["post"], parser_classes=[MultiPartParser, FormParser, JSONParser], url_path="info")
    @transaction.atomic
    def set_info(self, request):
        try:
            artist = Artist.objects.get(user=request.user)
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
