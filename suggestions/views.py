from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Suggestion
from .serializers import SuggestionSerializer
from artists.models import Artist
from spaces.models import Space
from notifications.models import Notification   # ✅ 추가


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


class SuggestionViewSet(viewsets.ModelViewSet):
    queryset = Suggestion.objects.all().order_by("-created_at")
    serializer_class = SuggestionSerializer

    @action(detail=True, methods=["post"])
    def read(self, request, pk=None):
        """제안서 읽음 처리"""
        suggestion = self.get_object()
        suggestion.is_read = True
        suggestion.save()
        return Response({"detail": "읽음 처리 완료", "is_read": suggestion.is_read}, status=status.HTTP_200_OK)

    # 생성 가드
    def _guard_sender(self, request, sender_type, artist: Artist, space: Space):
        if request.user.is_superuser:
            return None
        if not request.user.is_authenticated:
            return forbidden("인증 필요")
        if sender_type == Suggestion.SENDER_ARTIST:
            if request.user.id != artist.user_id:
                return forbidden("본인 아티스트 프로필로만 제안할 수 있습니다.", "artist_id")
        elif sender_type == Suggestion.SENDER_SPACE:
            if request.user.id != space.user_id:
                return forbidden("본인 공간 프로필로만 제안할 수 있습니다.", "space_id")
        return None

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data, context={"request": request})
        if not ser.is_valid():
            return bad_request(str(ser.errors))

        sender_type = ser.validated_data["sender_type"]
        artist = ser.validated_data["artist"]
        space = ser.validated_data["space"]

        guard = self._guard_sender(request, sender_type, artist, space)
        if guard:
            return guard

        instance = ser.save()

        # ✅ 알림 생성: 제안 수신자에게 알림 발송
        if sender_type == Suggestion.SENDER_ARTIST:
            target_user = space.user
            msg = f"{artist.name} 아티스트가 {space.place_name} 공간에 제안을 보냈습니다."
            link = f"http://127.0.0.1:8000/api/v1/suggestions/{instance.id}/"
        else:
            target_user = artist.user
            msg = f"{space.place_name} 공간이 {artist.name} 아티스트에게 제안을 보냈습니다."
            link = f"http://127.0.0.1:8000/api/v1/suggestions/{instance.id}/"

        Notification.objects.create(
            user=target_user,
            content=msg,
            target_link=link
        )

        out = self.get_serializer(instance, context={"request": request}).data
        return Response(out, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"])
    def received(self, request):
        r_type = request.query_params.get("receiver_type")
        r_id = request.query_params.get("receiver_id")
        if r_type not in (Suggestion.SENDER_ARTIST, Suggestion.SENDER_SPACE) or not r_id:
            return bad_request("receiver_type('artist'|'space')와 receiver_id는 필수입니다.", "receiver")

        if r_type == Suggestion.SENDER_ARTIST:
            try:
                artist = Artist.objects.get(pk=r_id)
            except Artist.DoesNotExist:
                return bad_request("존재하지 않는 artist_id 입니다.", "receiver_id")
            if not request.user.is_superuser and request.user.id != artist.user_id:
                return forbidden("본인 아티스트 제안함만 조회할 수 있습니다.", "receiver_id")
            qs = self.queryset.filter(artist=artist)
        else:
            try:
                space = Space.objects.get(pk=r_id)
            except Space.DoesNotExist:
                return bad_request("존재하지 않는 space_id 입니다.", "receiver_id")
            if not request.user.is_superuser and request.user.id != space.user_id:
                return forbidden("본인 공간 제안함만 조회할 수 있습니다.", "receiver_id")
            qs = self.queryset.filter(space=space)

        page = self.paginate_queryset(qs.order_by("-created_at"))
        ser = self.get_serializer(page or qs, many=True, context={"request": request})
        if page is not None:
            return self.get_paginated_response(ser.data)
        return Response(ser.data, status=200)

    @action(detail=False, methods=["get"])
    def sent(self, request):
        s_type = request.query_params.get("sender_type")
        s_id = request.query_params.get("sender_id")
        if s_type not in (Suggestion.SENDER_ARTIST, Suggestion.SENDER_SPACE) or not s_id:
            return bad_request("sender_type('artist'|'space')와 sender_id는 필수입니다.", "sender")

        if s_type == Suggestion.SENDER_ARTIST:
            try:
                artist = Artist.objects.get(pk=s_id)
            except Artist.DoesNotExist:
                return bad_request("존재하지 않는 artist_id 입니다.", "sender_id")
            if not request.user.is_superuser and request.user.id != artist.user_id:
                return forbidden("본인 아티스트 발신함만 조회할 수 있습니다.", "sender_id")
            qs = self.queryset.filter(sender_type=Suggestion.SENDER_ARTIST, artist=artist)
        else:
            try:
                space = Space.objects.get(pk=s_id)
            except Space.DoesNotExist:
                return bad_request("존재하지 않는 space_id 입니다.", "sender_id")
            if not request.user.is_superuser and request.user.id != space.user_id:
                return forbidden("본인 공간 발신함만 조회할 수 있습니다.", "sender_id")
            qs = self.queryset.filter(sender_type=Suggestion.SENDER_SPACE, space=space)

        page = self.paginate_queryset(qs.order_by("-created_at"))
        ser = self.get_serializer(page or qs, many=True, context={"request": request})
        if page is not None:
            return self.get_paginated_response(ser.data)
        return Response(ser.data, status=200)

    @action(detail=True, methods=["patch"])
    @transaction.atomic
    def accept(self, request, pk=None):
        sugg: Suggestion = self.get_object()
        receiver_user_id = sugg.space.user_id if sugg.sender_type == Suggestion.SENDER_ARTIST else sugg.artist.user_id
        if not request.user.is_superuser and request.user.id != receiver_user_id:
            return forbidden("제안 수신자만 수락할 수 있습니다.", "accept")

        sugg.is_accepted = True
        sugg.save(update_fields=["is_accepted", "updated_at"])

        # ✅ 알림 생성
        target_user = sugg.artist.user if sugg.sender_type == Suggestion.SENDER_SPACE else sugg.space.user
        Notification.objects.create(
            user=target_user,
            content=f"'{sugg}' 제안이 수락되었습니다.",
            target_link=f"http://127.0.0.1:8000/api/v1/suggestions/{sugg.id}/"
        )

        data = self.get_serializer(sugg, context={"request": request}).data
        return Response(data, status=200)

    @action(detail=True, methods=["patch"])
    @transaction.atomic
    def status(self, request, pk=None):
        if not request.user.is_superuser:
            return forbidden("관리자만 변경할 수 있습니다.", "status")

        sugg: Suggestion = self.get_object()
        val = request.data.get("is_accepted", None)
        if val not in (True, False, None, "true", "false", "null"):
            return bad_request("is_accepted는 true/false/null 이어야 합니다.", "is_accepted")

        if isinstance(val, str):
            val = {"true": True, "false": False, "null": None}.get(val.lower(), None)

        sugg.is_accepted = val
        sugg.save(update_fields=["is_accepted", "updated_at"])

        # ✅ 알림 생성
        if val is True:
            target_user = sugg.artist.user if sugg.sender_type == Suggestion.SENDER_SPACE else sugg.space.user
            Notification.objects.create(
                user=target_user,
                content=f"관리자에 의해 '{sugg}' 제안이 수락 처리되었습니다.",
                target_link=f"http://127.0.0.1:8000/api/v1/suggestions/{sugg.id}/"
            )

        return Response(self.get_serializer(sugg, context={"request": request}).data, status=200)
