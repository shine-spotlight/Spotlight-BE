from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db import transaction

from .models import Posting
from .serializers import PostingSerializer
from suggestions.models import Suggestion
from artists.models import Artist


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

    # 권한 가드: 생성/수정/삭제는 공간 소유자 또는 관리자만
    def _guard_space_owner(self, request, posting_or_space):
        space = posting_or_space.space if isinstance(posting_or_space, Posting) else posting_or_space

        if request.user.is_superuser:   # ✅ 관리자면 무조건 허용
            return None

        if not request.user.is_authenticated:
            return forbidden("인증 필요")

        if getattr(request.user, "id", None) != getattr(space.user, "id", None):
            return forbidden("본인 공간의 공고만 생성/수정/삭제할 수 있습니다.")

        return None

    # 공연 공고 생성
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

    # 공연 공고 수정
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

    # 공연 공고 삭제
    def destroy(self, request, *args, **kwargs):
        posting = self.get_object()
        guard = self._guard_space_owner(request, posting)
        if guard:
            return guard

        posting.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # 공연 공고 전체 조회 (필터링)
    # GET /api/v1/postings/?category=1&date_from=2025-01-01&date_to=2025-12-31&price_type=paid
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

    # 공고 기반 제안 전송 (아티스트 → 공간)
    # POST /api/v1/postings/{posting_pk}/suggestion/
    @action(detail=True, methods=["post"], url_path="suggestion")
    @transaction.atomic
    def send_suggestion(self, request, pk=None):
        posting = self.get_object()
        artist_id = request.data.get("artist_id")
        message = request.data.get("message")

        if not artist_id:
            return bad_request("artist_id는 필수입니다.", "artist_id")
        if not message or not str(message).strip():
            return bad_request("message는 필수입니다.", "message")

        # sender 권한 가드: 본인 Artist인지 확인
        try:
            artist = Artist.objects.get(pk=artist_id)
        except Artist.DoesNotExist:
            return bad_request("존재하지 않는 artist_id 입니다.", "artist_id")

        if not request.user.is_superuser:   # ✅ 관리자면 무조건 통과
            if getattr(request.user, "id", None) != getattr(artist.user, "id", None):
                return forbidden("본인 아티스트 프로필로만 제안할 수 있습니다.", "artist_id")

        # 중복 제안 방지
        exists = Suggestion.objects.filter(
            artist_id=artist.id,
            space_id=posting.space_id,
            is_accepted__isnull=True,
        ).exists()
        if exists:
            return bad_request("동일 아티스트/공간 조합의 진행중 제안이 존재합니다.", "suggestion")

        # Suggestion 모델에 posting_id 필드가 있을 때만 값 세팅
        sugg_kwargs = {
            "sender_type": "artist",
            "artist_id": artist.id,
            "space_id": posting.space_id,
            "message": message,
        }
        if "posting_id" in [f.name for f in Suggestion._meta.get_fields()]:
            sugg_kwargs["posting_id"] = posting.id

        sugg = Suggestion.objects.create(**sugg_kwargs)

        return Response({"suggestion_id": sugg.id, "created": True}, status=201)
