from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction

from .models import Like
from .serializers import LikeSerializer
from artists.models import Artist
from spaces.models import Space
from notifications.models import Notification


def bad_request(detail: str, field: str = ""):
    payload = {"detail": detail, "code": "invalid_param"}
    if field:
        payload["field"] = field
    return Response(payload, status=400)


def forbidden(detail: str, field: str = ""):
    payload = {"detail": detail, "code": "permission_denied"}
    if field:
        payload["field"] = field
    return Response(payload, status=403)


class LikeViewSet(viewsets.GenericViewSet):
    queryset = Like.objects.all().order_by("-created_at")
    serializer_class = LikeSerializer
    permission_classes = [IsAuthenticated]   # ✅ 토큰 필수

    # 1) 아티스트 찜 토글
    @swagger_auto_schema(
        operation_summary="아티스트 찜 토글",
        operation_description="""
아티스트를 찜하거나 찜을 해제합니다.

- 이 API는 **공간 보유자(공간 계정)**만 사용할 수 있습니다.
- 이미 찜한 상태에서 다시 요청하면 찜이 해제됩니다.
- 요청 body에는 artist_id만 입력하면 됩니다.

**예시 요청**
```json
POST /api/v1/likes/artists/
{
  "artist_id": 2
}
```
**응답**
- 찜 성공: {"liked": true} (201)
- 찜 해제: {"liked": false} (200)
""",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'artist_id': openapi.Schema(type=openapi.TYPE_INTEGER, description="아티스트 ID (필수)")
            },
            required=['artist_id']
        ),
        responses={
            201: openapi.Response(description="찜 성공", examples={"application/json": {"liked": True}}),
            200: openapi.Response(description="찜 해제", examples={"application/json": {"liked": False}})
        },
        tags=["Like"]
    )
    @action(detail=False, methods=["post"], url_path="artists")
    @transaction.atomic
    def like_artist(self, request):
        artist_id = request.data.get("artist_id")
        if not artist_id:
            return bad_request("artist_id는 필수입니다.", "artist_id")

        try:
            artist = Artist.objects.get(pk=artist_id)
        except Artist.DoesNotExist:
            return bad_request("존재하지 않는 artist_id 입니다.", "artist_id")

        if not request.user.is_superuser and request.user.role != "space":
            return forbidden("아티스트는 공간 보유자만 찜할 수 있습니다.", "role")

        like, created = Like.objects.get_or_create(
            user=request.user,   # ✅ 토큰 사용자 그대로 사용
            artist=artist
        )
        if not created:
            like.delete()
            return Response({"liked": False}, status=200)

        # 알림 발송
        Notification.objects.create(
            user=artist.user,
            content=f"{request.user} 님이 {artist.name} 아티스트를 찜했습니다.",
            target_link=f"/api/v1/artists/{artist.id}/"
        )
        return Response({"liked": True}, status=201)

    # 2) 공간 찜 토글
    @swagger_auto_schema(
        operation_summary="공간 찜 토글",
        operation_description="""
공간을 찜하거나 찜을 해제합니다.

- 이 API는 **아티스트 계정**만 사용할 수 있습니다.
- 이미 찜한 상태에서 다시 요청하면 찜이 해제됩니다.
- 요청 body에는 space_id만 입력하면 됩니다.

**예시 요청**
```json
POST /api/v1/likes/spaces/
{
  "space_id": 3
}
```
**응답**
- 찜 성공: {"liked": true} (201)
- 찜 해제: {"liked": false} (200)
""",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'space_id': openapi.Schema(type=openapi.TYPE_INTEGER, description="공간 ID (필수)")
            },
            required=['space_id']
        ),
        responses={
            201: openapi.Response(description="찜 성공", examples={"application/json": {"liked": True}}),
            200: openapi.Response(description="찜 해제", examples={"application/json": {"liked": False}})
        },
        tags=["Like"]
    )
    @action(detail=False, methods=["post"], url_path="spaces")
    @transaction.atomic
    def like_space(self, request):
        space_id = request.data.get("space_id")
        if not space_id:
            return bad_request("space_id는 필수입니다.", "space_id")

        try:
            space = Space.objects.get(pk=space_id)
        except Space.DoesNotExist:
            return bad_request("존재하지 않는 space_id 입니다.", "space_id")

        if not request.user.is_superuser and request.user.role != "artist":
            return forbidden("공간은 아티스트만 찜할 수 있습니다.", "role")

        like, created = Like.objects.get_or_create(
            user=request.user,   # ✅ 토큰 사용자 그대로 사용
            space=space
        )
        if not created:
            like.delete()
            return Response({"liked": False}, status=200)

        Notification.objects.create(
            user=space.user,
            content=f"{request.user} 님이 {space.place_name} 공간을 찜했습니다.",
            target_link=f"/api/v1/spaces/{space.id}/"
        )
        return Response({"liked": True}, status=201)

    # 3) 내가 찜한 목록
    @swagger_auto_schema(
        operation_summary="내가 찜한 목록 조회",
        operation_description="""
현재 로그인한 사용자가 찜한 아티스트/공간 목록을 조회합니다.

- 반드시 토큰 인증이 필요합니다.
- 본인 찜 목록만 조회할 수 있습니다.
- 페이지네이션이 적용됩니다.
""",
        responses={200: LikeSerializer(many=True)},
        tags=["Like"]
    )
    def list(self, request, *args, **kwargs):
        qs = self.queryset.filter(user=request.user)   # ✅ query param 제거
        page = self.paginate_queryset(qs)
        ser = self.get_serializer(page or qs, many=True)
        if page is not None:
            return self.get_paginated_response(ser.data)
        return Response(ser.data, status=200)