from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db import transaction
from suggestions.serializers import SuggestionSerializer

from .models import Posting
from .serializers import PostingSerializer
from suggestions.models import Suggestion
from artists.models import Artist
from rest_framework.permissions import IsAuthenticated
from spaces.models import Space
import json


def bad_request(detail: str, field: str):
    return Response(
        {"detail": detail, "code": "invalid_param", "field": field},
        status=400
    )


def forbidden(detail: str, field: str = "posting_pk"):
    return Response(
        {"detail": detail, "code": "permission_denied", "field": field},
        status=403
    )


def _norm_to_list_for_filter(value):
    """문자열/리스트/None → list[str]로 변환 (필터링용)"""
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(x).strip() for x in value if str(x).strip()]
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return []
        # JSON 배열 문자열 처리
        try:
            parsed = json.loads(s)
            if isinstance(parsed, (list, tuple)):
                return [str(x).strip() for x in parsed if str(x).strip()]
        except Exception:
            pass
        # 쉼표로 구분된 문자열 처리
        if "," in s:
            return [x.strip() for x in s.split(",") if x.strip()]
        return [s]
    return []


class PostingViewSet(viewsets.ModelViewSet):
    queryset = Posting.objects.all().order_by("-created_at")
    serializer_class = PostingSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def _guard_space_owner(self, request, posting_or_space):
        space = posting_or_space.space if isinstance(posting_or_space, Posting) else posting_or_space

        if request.user.is_superuser:
            return None

        if not request.user.is_authenticated:
            return forbidden("인증 필요")

        if getattr(request.user, "id", None) != getattr(space.user, "id", None):
            return forbidden("본인 공간의 공고만 생성/수정/삭제할 수 있습니다.")

        return None

    # 공연 공고 생성 (POST)
    @swagger_auto_schema(
        operation_summary="공연 공고 생성",
        operation_description="""
새로운 공연 공고를 등록합니다. (공간 소유자만 가능)

**중요**
- 프론트는 space_id를 절대 body에 넣지 마세요. 서버에서 토큰 기반으로 자동 매핑합니다.
- 공간 소유자(role=space)만 생성할 수 있습니다.

**필수 필드:**
- title: 공고 제목
- description: 공고 설명
- categories: 카테고리 배열
- price_type: "paid" | "free" | "negotiable"
- date: 공연 날짜

**선택 필드:**
- posting_image: 공고 이미지 파일
- price_amount: 가격(유료일 때만)
""",
        request_body=PostingSerializer,
        responses={201: PostingSerializer, 400: "유효성 오류"},
        tags=["Posting"]
    )
    def create(self, request, *args, **kwargs):
        user = request.user
        if not hasattr(user, "role") or user.role != "space":
            return forbidden("공간 소유자만 공고를 생성할 수 있습니다.", "role")

        try:
            space = Space.objects.get(user=user)
        except Space.DoesNotExist:
            return bad_request("해당 유저의 공간 프로필이 없습니다.", "space")

        data = request.data.copy()
        data.pop("space", None)
        data.pop("space_id", None)

        ser = self.get_serializer(data=data)
        ser.is_valid(raise_exception=True)

        posting = ser.save(space=space)
        return Response(self.get_serializer(posting).data, status=status.HTTP_201_CREATED)

    # 공연 공고 수정 (PUT)
    @swagger_auto_schema(
        operation_summary="공연 공고 수정",
        operation_description="공연 공고 정보를 수정합니다. (공간 소유자 또는 관리자만 가능)",
        request_body=PostingSerializer,
        responses={200: PostingSerializer, 400: "유효성 오류"},
        tags=["Posting"]
    )
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    # 공연 공고 삭제 (DELETE)
    @swagger_auto_schema(
        operation_summary="공연 공고 삭제",
        responses={204: "삭제 성공", 403: "권한 없음"},
        tags=["Posting"]
    )
    def destroy(self, request, *args, **kwargs):
        posting = self.get_object()
        guard = self._guard_space_owner(request, posting)
        if guard:
            return guard
        posting.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # 공연 공고 전체 조회 (GET)
    @swagger_auto_schema(
        operation_summary="공연 공고 전체 조회",
        manual_parameters=[
            openapi.Parameter('categories', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='카테고리 이름 배열 (쉼표구분)', required=False),
            openapi.Parameter('price_type', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='유/무료', required=False),
            openapi.Parameter('date_from', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='시작일', required=False),
            openapi.Parameter('date_to', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='종료일', required=False),
            openapi.Parameter('place_region', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='공간 지역명', required=False),
        ],
        responses={200: PostingSerializer(many=True)},
        tags=["Posting"]
    )
    def list(self, request, *args, **kwargs):
        qs = self.queryset
        categories = request.query_params.get("categories")
        price_type = request.query_params.get("price_type")
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")
        place_region = request.query_params.get("place_region")

        if categories:
            categories_list = _norm_to_list_for_filter(categories)
            if categories_list:
                qs = qs.filter(categories__name__in=categories_list)

        if price_type:
            qs = qs.filter(price_type=price_type)
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)

        if place_region:
            place_region_list = _norm_to_list_for_filter(place_region)
            if place_region_list:
                qs = qs.filter(space__place_region__contains=place_region_list)

        page = self.paginate_queryset(qs)
        ser = self.get_serializer(page or qs, many=True)
        if page is not None:
            return self.get_paginated_response(ser.data)
        return Response(ser.data, status=200)

    # 공연 공고 상세 조회 (GET)
    @swagger_auto_schema(
        operation_summary="공연 공고 상세 조회",
        responses={200: PostingSerializer, 404: "존재하지 않음"},
        tags=["Posting"]
    )
    def retrieve(self, request, *args, **kwargs):
        posting = self.get_object()
        ser = self.get_serializer(posting)
        return Response(ser.data, status=200)

    # 제안 전송 (POST)
    @swagger_auto_schema(
        operation_summary="공고 기반 제안 전송",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={'message': openapi.Schema(type=openapi.TYPE_STRING, description="제안 메시지 (필수)")},
            required=['message']
        ),
        tags=["Posting"]
    )
    @action(detail=True, methods=["post"], url_path="suggestion", permission_classes=[IsAuthenticated])
    def send_suggestion(self, request, pk=None):
        posting = self.get_object()
        user = request.user

        if not hasattr(user, "role") or user.role != "artist":
            return forbidden("아티스트만 제안을 보낼 수 있습니다.", "role")

        try:
            my_artist = Artist.objects.get(user=user)
        except Artist.DoesNotExist:
            return Response({"detail": "아티스트 프로필이 없습니다."}, status=400)

        message = request.data.get("message", "").strip()
        if not message:
            return Response({"detail": "message는 필수입니다."}, status=400)

        suggestion = Suggestion.objects.create(
            sender_type=Suggestion.SENDER_ARTIST,
            artist=my_artist,
            space=posting.space,
            posting=posting,
            message=message
        )
        return Response(SuggestionSerializer(suggestion).data, status=201)

    # 공연 공고 부분 수정 (PATCH)
    @swagger_auto_schema(
        operation_summary="공연 공고 부분 수정",
        request_body=PostingSerializer,
        responses={200: PostingSerializer, 400: "유효성 오류"},
        tags=["Posting"]
    )
    def partial_update(self, request, *args, **kwargs):
        posting = self.get_object()
        guard = self._guard_space_owner(request, posting)
        if guard:
            return guard

        serializer = self.get_serializer(posting, data=request.data, partial=True)
        if serializer.is_valid():
            posting = serializer.save()
            return Response(self.get_serializer(posting).data, status=200)
        return bad_request(str(serializer.errors), "partial_update")
