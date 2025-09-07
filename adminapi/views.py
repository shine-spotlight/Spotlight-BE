from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import F

from artists.models import Artist
from spaces.models import Space
from postings.models import Posting
from points.models import PointTransaction
from notifications.models import Notification
from artists.serializers import ArtistSerializer
from spaces.serializers import SpaceSerializer
from points.serializers import PointTransactionSerializer
from notifications.serializers import NotificationSerializer
from users.models import User


def forbidden(detail: str, field: str = ""):
    payload = {"detail": detail, "code": "permission_denied"}
    if field:
        payload["field"] = field
    return Response(payload, status=403)


class AdminViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def _check_admin(self, request):
        if not request.user.is_staff:
            return forbidden("관리자만 접근할 수 있습니다.", "admin")
        return None

    # 아티스트 강제 조회
    @action(detail=False, methods=["get"], url_path="artists")
    def list_artists(self, request):
        guard = self._check_admin(request)
        if guard:
            return guard
        qs = Artist.objects.all().order_by("-created_at")
        return Response(ArtistSerializer(qs, many=True).data, status=200)

    # 아티스트 강제 수정
    @action(detail=False, methods=["patch"], url_path="artists/(?P<artist_pk>[^/.]+)")
    def update_artist(self, request, artist_pk=None):
        guard = self._check_admin(request)
        if guard:
            return guard
        try:
            artist = Artist.objects.get(pk=artist_pk)
        except Artist.DoesNotExist:
            return Response({"detail": "존재하지 않는 아티스트"}, status=404)
        ser = ArtistSerializer(artist, data=request.data, partial=True)
        if ser.is_valid():
            ser.save()
            return Response(ser.data, status=200)
        return Response(ser.errors, status=400)

    # 공간 강제 조회
    @action(detail=False, methods=["get"], url_path="spaces")
    def list_spaces(self, request):
        guard = self._check_admin(request)
        if guard:
            return guard
        qs = Space.objects.all().order_by("-created_at")
        return Response(SpaceSerializer(qs, many=True).data, status=200)

    # 공간 강제 수정
    @action(detail=False, methods=["patch"], url_path="spaces/(?P<space_pk>[^/.]+)")
    def update_space(self, request, space_pk=None):
        guard = self._check_admin(request)
        if guard:
            return guard
        try:
            space = Space.objects.get(pk=space_pk)
        except Space.DoesNotExist:
            return Response({"detail": "존재하지 않는 공간"}, status=404)
        ser = SpaceSerializer(space, data=request.data, partial=True)
        if ser.is_valid():
            ser.save()
            return Response(ser.data, status=200)
        return Response(ser.errors, status=400)

    # 공연 공고 강제 삭제
    @action(detail=False, methods=["delete"], url_path="postings/(?P<posting_pk>[^/.]+)")
    def delete_posting(self, request, posting_pk=None):
        guard = self._check_admin(request)
        if guard:
            return guard
        try:
            posting = Posting.objects.get(pk=posting_pk)
        except Posting.DoesNotExist:
            return Response({"detail": "존재하지 않는 공고"}, status=404)
        posting.delete()
        return Response(status=204)

    # 포인트 내역 전체 조회
    @action(detail=False, methods=["get"], url_path="points/history")
    def all_points_history(self, request):
        guard = self._check_admin(request)
        if guard:
            return guard
        qs = PointTransaction.objects.all().order_by("-created_at")
        return Response(PointTransactionSerializer(qs, many=True).data, status=200)

    # 포인트 잔액 전체 조회 (유저별 목록)
    @action(detail=False, methods=["get"], url_path="points/balance")
    def all_points_balance(self, request):
        guard = self._check_admin(request)
        if guard:
            return guard

        result = []
        users = User.objects.all()
        for u in users:
            qs = PointTransaction.objects.filter(user=u)
            balance = sum([tx.amount if tx.transaction_type == "charge" else -tx.amount for tx in qs])
            result.append({"user_id": u.id, "balance": balance})

        return Response(result, status=200)

    # 알림 강제 발송
    @action(detail=False, methods=["post"], url_path="notifications")
    def send_notification(self, request):
        guard = self._check_admin(request)
        if guard:
            return guard

        user_id = request.data.get("user")
        content = request.data.get("content")
        target_link = request.data.get("target_link")

        if not user_id or not content or not target_link:
            return Response({"detail": "user, content, target_link는 필수입니다."}, status=400)

        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({"detail": "존재하지 않는 user_id"}, status=400)

        notif = Notification.objects.create(
            user=user,
            content=content,
            target_link=target_link
        )
        return Response(NotificationSerializer(notif).data, status=201)
