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

    # 공연 공고 생성 (POST임)
    @swagger_auto_schema(
        operation_summary="공연 공고 생성",
        operation_description="""
새로운 공연 공고를 등록합니다. (공간 소유자 또는 관리자만 가능)

**필수 필드:**
- space_id: 공간 PK (본인 소유 공간만 가능)
- title: 공고 제목
- description: 공고 설명
- categories: 카테고리 PK 배열
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
        ser = self.get_serializer(data=request.data)
        if not ser.is_valid():
            return bad_request(str(ser.errors), "create")

        space = ser.validated_data["space"]
        guard = self._guard_space_owner(request, space)
        if guard:
            return guard

        posting = ser.save()
        return Response(self.get_serializer(posting).data, status=status.HTTP_201_CREATED)

    # 공연 공고 수정 (PUT)
    @swagger_auto_schema(
        operation_summary="공연 공고 수정",
        operation_description="""
기존 공연 공고의 정보를 수정합니다. (공간 소유자 또는 관리자만 가능)

**수정 가능한 필드:**  
- space_id, title, description, categories, price_type, price_amount, date, posting_image
""",
        request_body=PostingSerializer,
        responses={200: PostingSerializer, 400: "유효성 오류"},
        tags=["Posting"]
    )
    def update(self, request, *args, **kwargs):
        posting = self.get_object()
        guard = self._guard_space_owner(request, posting)
        if guard:
            return guard

        partial = kwargs.pop("partial", False)
        ser = self.get_serializer(posting, data=request.data, partial=partial)
        if ser.is_valid():
            posting = ser.save()
            return Response(self.get_serializer(posting).data, status=200)
        return bad_request(str(ser.errors), "update")

    # 공연 공고 삭제 (DELETE)
    @swagger_auto_schema(
        operation_summary="공연 공고 삭제",
        operation_description="""
특정 공연 공고를 삭제합니다. (공간 소유자 또는 관리자만 가능)

**주의:** 삭제된 데이터는 복구할 수 없습니다.
""",
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
        operation_description="""
등록된 모든 공연 공고를 필터 조건(category, price_type, date_from, date_to)로 조회합니다.

- category: 카테고리 PK
- price_type: "paid" | "free" | "negotiable"
- date_from: 공연 시작일(YYYY-MM-DD)
- date_to: 공연 종료일(YYYY-MM-DD)

**응답:**  
- space: 공간명  
- space_address: 공간 주소  
- categories: 카테고리 PK 배열  
- category_names: 카테고리명 배열  
- 기타 공고 정보
""",
        manual_parameters=[
            openapi.Parameter('category', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description='카테고리 PK', required=False),
            openapi.Parameter('price_type', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='유/무료', required=False),
            openapi.Parameter('date_from', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='시작일', required=False),
            openapi.Parameter('date_to', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='종료일', required=False),
        ],
        responses={200: PostingSerializer(many=True)},
        tags=["Posting"]
    )
    def list(self, request, *args, **kwargs):
        qs = self.queryset
        category = request.query_params.get("category")
        price_type = request.query_params.get("price_type")
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")

        if category:
            qs = qs.filter(categories__id=category)
        if price_type:
            qs = qs.filter(price_type=price_type)
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)

        page = self.paginate_queryset(qs)
        ser = self.get_serializer(page or qs, many=True)
        if page is not None:
            return self.get_paginated_response(ser.data)
        return Response(ser.data, status=200)
    
    # 공연 공고 상세 조회 (GET)
    @swagger_auto_schema(
        operation_summary="공연 공고 상세 조회",
        operation_description="""
특정 공연 공고의 상세 정보를 조회합니다.

**포함 정보:**
- space: 공간명
- space_address: 공간 주소
- categories: 카테고리 PK 배열
- category_names: 카테고리명 배열
- 기타 공고 정보
""",
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
        operation_description="""
아티스트가 특정 공연 공고에 대해 공간에 제안을 보냅니다.

- 이 API는 **아티스트만** 사용할 수 있습니다.
- 요청 URL의 {id}는 제안하려는 공연 공고의 id입니다.
- 요청 body에는 **message**만 입력하면 됩니다.
- 아티스트 정보는 토큰(로그인)에서 자동으로 추출됩니다.
- 공간 정보는 해당 공고의 space로 자동 연결됩니다.

**예시 요청**
```json
POST /api/v1/postings/1/suggestion/
{
  "message": "이 공연에 참여하고 싶어요!"
}
```
""",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'message': openapi.Schema(type=openapi.TYPE_STRING, description="제안 메시지 (필수)")
            },
            required=['message']
        ),
        responses={
            201: openapi.Response(
                description="제안 생성 결과",
                examples={"application/json": {
                    "id": 1,
                    "artist": 2,
                    "space": 3,
                    "posting": 1,
                    "message": "이 공연에 참여하고 싶어요!",
                    "is_accepted": False,
                    "is_read": False,
                    "created_at": "2025-09-14T12:34:56Z"
                }}
            ),
            400: "유효성 오류"
        },
        tags=["Posting"]
    )
    @action(detail=True, methods=["post"], url_path="suggestion", permission_classes=[IsAuthenticated])
    def send_suggestion(self, request, pk=None):
        posting = self.get_object()
        user = request.user

        # 1번: 아티스트만 접근 가능하게 role 체크
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
    
    @swagger_auto_schema(auto_schema=None) 
    def partial_update(self, request, *args, **kwargs):
        pass