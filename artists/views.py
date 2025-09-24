from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db import transaction
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q

from .models import Artist
from artistequipments.models import ArtistEquipment
from .serializers import ArtistSerializer
from equipmentcategories.models import EquipmentCategory
from users.permissions import IsOwnerOrReadOnlyWithAdminPass
from rest_framework.exceptions import ValidationError, PermissionDenied
import json
import ast
from categories.models import Category

# 에러 포맷 통일
def bad_request(detail: str, field: str):
    return Response({"detail": detail, "code": "invalid_param", "field": field}, status=400)

def forbidden(detail: str, field: str = "artist_pk"):
    return Response({"detail": detail, "code": "permission_denied", "field": field}, status=403)

def _norm_to_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    s = str(value).strip()
    return [s] if s else []

def _norm_name(name: str) -> str:
    # 공백 정리 및 소문자 변환
    return " ".join(str(name).strip().split()).lower()

def _norm_json(value, field="value"):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        # 리스트 내부 값도 정규화
        return [_norm_name(v) if isinstance(v, str) else v for v in value]
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return []
        try:
            parsed = json.loads(s)
            if isinstance(parsed, (list, tuple)):
                return [_norm_name(v) if isinstance(v, str) else v for v in parsed]
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
        try:
            parsed = ast.literal_eval(s)
            if isinstance(parsed, (list, tuple)):
                return [_norm_name(v) if isinstance(v, str) else v for v in parsed]
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
        return [_norm_name(s)]
    return [value]

class ArtistViewSet(viewsets.ModelViewSet):
    queryset = Artist.objects.all()
    serializer_class = ArtistSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    permission_classes = [IsOwnerOrReadOnlyWithAdminPass]

    # 아티스트 생성 (POST)
    @swagger_auto_schema(
        operation_summary="아티스트 생성",
        operation_description="""
아티스트 프로필을 최초로 생성합니다.

**필수 필드:**
- name: 아티스트명
- categories: 카테고리명 배열 (예: ["음악", "무용"])

**선택 필드:**
- bio: 소개글
- number_of_members: 팀원 수 (기본값: 1)
- custom_category: 커스텀 카테고리
- profile_image: 프로필 이미지 파일
- portfolio_links: 포트폴리오 링크 배열
- region: 활동 지역 배열
- desired_pay: 희망 페이
- is_free_allowed: 무료 공연 가능 여부
- equipments: 보유 장비 배열 *출력은 equipments_display*

**예시 요청 (JSON):**
```json
{
  "name": "밴드A",
  "categories": ["음악", "무용"],
  "bio": "록밴드입니다",
  "number_of_members": 4,
  "portfolio_links": ["https://youtube.com/...", "https://soundcloud.com/..."],
  "region": ["서울", "경기"],
  "desired_pay": 100000,
  "is_free_allowed": true
}
```
""",
        tags=["Artist"]
    )
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        if Artist.objects.filter(user=request.user).exists():
            return bad_request("이미 아티스트 프로필이 있습니다.", "user")

        # ✅ deepcopy 방지 (파일 객체 그대로 둠)
        mutable_data = {k: request.data.get(k) for k in request.data.keys()}

        serializer = self.get_serializer(data=mutable_data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)

        self._handle_m2m_fields(mutable_data, serializer.instance)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    # 아티스트 전체 수정 (PUT)
    @swagger_auto_schema(
        operation_summary="아티스트 전체 수정",
        operation_description="""
아티스트 프로필 정보를 전체 수정합니다.

**사용 가능한 모든 필드:**
- name, categories (배열), bio, number_of_members
- custom_category, profile_image, portfolio_links
- region, desired_pay, is_free_allowed
-- equipments: 보유 장비 배열 *출력은 equipments_display*

**주의:** PUT 요청은 모든 필드를 다시 설정하므로, 유지하고 싶은 정보도 함께 전송해야 합니다.

**예시 요청:**
```json
{
  "name": "밴드A (수정됨)",
  "categories": ["음악"],
  "bio": "수정된 소개글",
  "number_of_members": 5,
  "portfolio_links": ["https://new-link.com"],
  "region": ["서울"],
  "desired_pay": 150000,
  "is_free_allowed": false
}
```
""",
        tags=["Artist"]
    )
    @transaction.atomic
    def update(self, request, *args, **kwargs):
        artist = self.get_object()
        if not (request.user.is_superuser or request.user.id == artist.user_id):
            return forbidden("본인만 수정 가능합니다")
        partial = kwargs.pop('partial', False)
        # _norm_json 적용
        mutable_data = {k: request.data.get(k) for k in request.data.keys()}

        for field in ["portfolio_links", "region"]:
            if field in mutable_data:
                try:
                    mutable_data[field] = _norm_json(mutable_data[field], field)
                except Exception:
                    return bad_request(f"{field}는 유효한 리스트/JSON이어야 합니다.", field)
        serializer = self.get_serializer(artist, data=mutable_data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        self._handle_m2m_fields(mutable_data, serializer.instance)
        return Response(serializer.data)

    # 아티스트 부분 수정 (PATCH)
    @swagger_auto_schema(
        operation_summary="아티스트 부분 수정",
        operation_description="""
아티스트 프로필 정보를 일부 수정합니다.

**수정하고 싶은 필드만 전송하면 됩니다:**
- name, categories (배열), bio, number_of_members
- custom_category, profile_image, portfolio_links
- region, desired_pay, is_free_allowed
- equipments: 보유 장비 배열 *출력은 equipments_display*
**예시 요청 (이름만 변경):**
```json
{
  "name": "새로운 아티스트명"
}
```

**예시 요청 (카테고리만 변경):**
```json
{
  "categories": ["무용", "연극"]
}
```
""",
        tags=["Artist"]
    )
    @transaction.atomic
    def partial_update(self, request, *args, **kwargs):
        artist = self.get_object()
        if not (request.user.is_superuser or request.user.id == artist.user_id):
            return forbidden("본인만 수정 가능합니다")
        # _norm_json 적용
        mutable_data = request.data.copy()
        for field in ["portfolio_links", "region"]:
            if field in mutable_data:
                try:
                    mutable_data[field] = _norm_json(mutable_data[field], field)
                except Exception:
                    return bad_request(f"{field}는 유효한 리스트/JSON이어야 합니다.", field)
        serializer = self.get_serializer(artist, data=mutable_data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        self._handle_m2m_fields(mutable_data, serializer.instance)
        return Response(serializer.data)

    # 아티스트 목록 조회 (GET)
    @swagger_auto_schema(
        operation_summary="아티스트 목록 조회",
        operation_description="""
모든 아티스트 프로필 리스트를 조회합니다.

**응답 정보:**
- 페이지네이션이 적용됩니다
- 카테고리 정보가 포함됩니다
- 프로필 이미지 URL이 포함됩니다

**응답 예시:**
```json
{
  "count": 50,
  "next": "http://api.example.com/artists/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "밴드A",
      "categories_display": ["음악", "무용"],
      "bio": "록밴드입니다",
      "number_of_members": 4,
      "profile_image": "http://example.com/media/artists/profile/image.jpg",
      "region": ["서울", "경기"],
      "desired_pay": 100000,
      "is_free_allowed": true,
      "phone_number": "010-1234-5678"
    }
  ]
}
```
""",
        tags=["Artist"]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    # 아티스트 상세 조회 (GET)
    @swagger_auto_schema(
        operation_summary="아티스트 상세 조회",
        operation_description="""
특정 아티스트 프로필의 상세 정보를 조회합니다.

**포함 정보:**
- 기본 프로필 정보
- 카테고리 목록 (categories_display)
- 포트폴리오 링크들
- 프로필 이미지 URL
- 연락처 정보

**응답 예시:**
```json
{
  "id": 1,
  "name": "밴드A",
  "categories_display": ["음악", "무용"],
  "bio": "록밴드입니다",
  "number_of_members": 4,
  "custom_category": "인디록",
  "portfolio_links": ["https://youtube.com/...", "https://soundcloud.com/..."],
  "profile_image": "http://example.com/media/artists/profile/image.jpg",
  "region": ["서울", "경기"],
  "desired_pay": 100000,
  "is_free_allowed": true,
  "phone_number": "010-1234-5678",
  "created_at": "2025-09-15T12:00:00Z"
}
```
""",
        tags=["Artist"]
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    # 아티스트 삭제 (DELETE)
    @swagger_auto_schema(
        operation_summary="아티스트 삭제",
        operation_description="""
아티스트 프로필을 삭제합니다.

**권한:**
- 본인 또는 관리자만 삭제 가능합니다
- 프로필 이미지 파일도 서버에서 삭제됩니다

**주의:** 삭제된 데이터는 복구할 수 없습니다.
""",
        tags=["Artist"]
    )
    def destroy(self, request, *args, **kwargs):
        artist = self.get_object()
        if not (request.user.is_superuser or request.user.id == artist.user_id):
            return forbidden("본인만 삭제 가능합니다")
        return super().destroy(request, *args, **kwargs)

    def perform_create(self, serializer):
        if self.request.user.role != "artist":
            raise PermissionDenied("아티스트 권한이 있는 유저만 가입할 수 있습니다.")
        serializer.save(user=self.request.user)
        self._handle_m2m_fields(self.request.data, serializer.instance)

    def perform_update(self, serializer):
        serializer.save()
        self._handle_m2m_fields(self.request.data, serializer.instance)

    def _handle_m2m_fields(self, data, artist):
        """
        equipments(name 배열)만 처리 (norm_name 적용)
        """
        equipments_names = _norm_json(data.get("equipments"), "equipments")
        if equipments_names:
            if not isinstance(equipments_names, (list, tuple)):
                raise ValidationError({"detail": "equipments는 배열이어야 합니다", "field": "equipments"})
            # norm_name이 이미 적용된 상태
            exists = list(EquipmentCategory.objects.filter(name__in=equipments_names).values_list("name", flat=True))
            missing = set(equipments_names) - set(exists)
            if missing:
                raise ValidationError({"detail": f"존재하지 않는 장비: {sorted(list(missing))}", "field": "equipments"})
            categories = EquipmentCategory.objects.filter(name__in=exists)
            ArtistEquipment.objects.filter(artist=artist).delete()
            ArtistEquipment.objects.bulk_create(
                [ArtistEquipment(artist=artist, category=cat) for cat in categories]
            )

    # 아티스트 필터링 (커스텀)
    @swagger_auto_schema(
        operation_summary="아티스트 필터링",
        operation_description="""
여러 조건(region, category, pay_min, pay_max)으로 아티스트를 필터링합니다.

- region: 지역 (부분 일치)
- category: 카테고리명 (정확 일치, 예: "음악")
- pay_min: 최소 페이
- pay_max: 최대 페이
""",
        manual_parameters=[
            openapi.Parameter('region', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='지역 (부분 일치, 예: "서울")'),
            openapi.Parameter('category', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='카테고리명 (정확 일치, 예: "음악")'),
            openapi.Parameter('pay_min', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description='최소 페이'),
            openapi.Parameter('pay_max', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description='최대 페이'),
        ],
        tags=["Artist"]
    )
    @transaction.atomic
    @action(detail=False, methods=["get"], url_path="filter")
    def filter_artists(self, request, *args, **kwargs):
        qs = self.queryset

        # region OR 검색 (JSONField, 배열 포함)
        regions = request.query_params.getlist("region")
        if regions:
            q = Q()
            for r in regions:
                # JSON 배열에 해당 원소가 포함되어 있는지 확인
                q |= Q(region__contains=[r])
            qs = qs.filter(q)

        # category OR 검색 (ManyToMany)
        categories = request.query_params.getlist("category")
        if categories:
            norm_categories = [_norm_name(c) for c in categories]
            cat_objs = Category.objects.filter(name__in=norm_categories)
            if cat_objs:
                q = Q()
                for cat in cat_objs:
                    q |= Q(categories=cat)
                qs = qs.filter(q)
            else:
                return Response({"detail": "존재하지 않는 카테고리"}, status=400)

        # pay_min, pay_max AND 조건
        pay_min = request.query_params.get("pay_min")
        pay_max = request.query_params.get("pay_max")
        if pay_min:
            qs = qs.filter(desired_pay__gte=int(pay_min))
        if pay_max:
            qs = qs.filter(desired_pay__lte=int(pay_max))

        page = self.paginate_queryset(qs.distinct().order_by("-id"))
        ser = self.get_serializer(page or qs, many=True)
        if page is not None:
            return self.get_paginated_response(ser.data)
        return Response(ser.data, status=200)

    @swagger_auto_schema(
        operation_summary="내 아티스트 프로필(me) 조회",
        operation_description="토큰 인증된 사용자의 아티스트 프로필 정보를 반환합니다. (url에 id 없이 /artists/me/로 접근)",
        responses={200: ArtistSerializer},
        tags=["Artist"]
    )
    @action(detail=False, methods=["get"], url_path="me", permission_classes=[IsAuthenticated])
    def me(self, request):
        """
        토큰 인증된 유저의 아티스트 프로필 정보 반환
        """
        try:
            artist = Artist.objects.get(user=request.user)
        except Artist.DoesNotExist:
            return Response({"detail": "해당 유저의 아티스트 프로필이 없습니다."}, status=404)
        return Response(ArtistSerializer(artist, context={"request": request}).data)