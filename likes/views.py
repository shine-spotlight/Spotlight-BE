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
    def list(self, request, *args, **kwargs):
        qs = self.queryset.filter(user=request.user)   # ✅ query param 제거
        page = self.paginate_queryset(qs)
        ser = self.get_serializer(page or qs, many=True)
        if page is not None:
            return self.get_paginated_response(ser.data)
        return Response(ser.data, status=200)
