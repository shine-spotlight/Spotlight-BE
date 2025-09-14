from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Suggestion
from .serializers import SuggestionSerializer
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

class SuggestionViewSet(viewsets.ModelViewSet):
    queryset = Suggestion.objects.all().order_by("-created_at")
    serializer_class = SuggestionSerializer
    permission_classes = [IsAuthenticated]
    from rest_framework.decorators import action


    @action(detail=False, methods=["get"], url_path="received")
    def received(self, request):
        """
        받은 제안함: 내 artist/space 프로필 기준으로 받은 제안만 반환
        """
        user = request.user
        role = getattr(user, "role", None)
        if role == "artist":
            my_artist = self._get_my_artist(user)
            if not my_artist:
                return bad_request("해당 유저의 Artist 프로필이 없습니다.", "artist")
            qs = self.queryset.filter(space__isnull=False, artist=my_artist)
        elif role == "space":
            my_space = self._get_my_space(user)
            if not my_space:
                return bad_request("해당 유저의 Space 프로필이 없습니다.", "space")
            qs = self.queryset.filter(artist__isnull=False, space=my_space)
        else:
            return bad_request("role은 'artist' 또는 'space'여야 합니다.", "role")

        page = self.paginate_queryset(qs)
        ser = self.get_serializer(page or qs, many=True)
        if page is not None:
            return self.get_paginated_response(ser.data)
        return Response(ser.data, status=200)

    @action(detail=False, methods=["get"], url_path="sent")
    def sent(self, request):
        """
        보낸 제안함: 내 artist/space 프로필 기준으로 보낸 제안만 반환
        """
        user = request.user
        role = getattr(user, "role", None)
        if role == "artist":
            my_artist = self._get_my_artist(user)
            if not my_artist:
                return bad_request("해당 유저의 Artist 프로필이 없습니다.", "artist")
            qs = self.queryset.filter(artist=my_artist)
        elif role == "space":
            my_space = self._get_my_space(user)
            if not my_space:
                return bad_request("해당 유저의 Space 프로필이 없습니다.", "space")
            qs = self.queryset.filter(space=my_space)
        else:
            return bad_request("role은 'artist' 또는 'space'여야 합니다.", "role")

        page = self.paginate_queryset(qs)
        ser = self.get_serializer(page or qs, many=True)
        if page is not None:
            return self.get_paginated_response(ser.data)
        return Response(ser.data, status=200)

    def _get_my_artist(self, user):
        try:
            return Artist.objects.get(user=user)
        except Artist.DoesNotExist:
            return None

    def _get_my_space(self, user):
        try:
            return Space.objects.get(user=user)
        except Space.DoesNotExist:
            return None

    def _receiver_from_body(self, data: dict):
        """
        body에서 receiver를 결정 (artist 또는 space 중 정확히 하나만 허용)
        반환: ("artist", Artist) or ("space", Space) or (None, None, 에러응답)
        """
        artist = data.get("artist")
        space  = data.get("space")

        # None, 빈문자열, "null", 0 등은 모두 False로 간주
        artist = artist if artist not in [None, "", "null", 0, "0"] else None
        space = space if space not in [None, "", "null", 0, "0"] else None

        if artist and space:
            return None, None, bad_request("artist와 space 중 하나만 지정해야 합니다.", "receiver")

        if not artist and not space:
            return None, None, bad_request("receiver가 없습니다. artist 또는 space 중 하나는 필수입니다.", "receiver")

        if artist:
            try:
                artist_obj = Artist.objects.get(pk=artist)
            except Artist.DoesNotExist:
                return None, None, bad_request("존재하지 않는 artist 입니다.", "artist")
            return "artist", artist_obj, None

        if space:
            try:
                space_obj = Space.objects.get(pk=space)
            except Space.DoesNotExist:
                return None, None, bad_request("존재하지 않는 space 입니다.", "space")
            return "space", space_obj, None

        return None, None, bad_request("receiver를 판별할 수 없습니다.", "receiver")

    def _notify(self, user, content, target_link):
        Notification.objects.create(
            user=user,
            content=content,
            target_link=target_link
        )

    @swagger_auto_schema(
        operation_summary="제안 생성",
        operation_description="""
아티스트 또는 공간이 상대에게 제안을 생성합니다.

- 토큰의 role(artist/space)로 본인 프로필이 자동 매핑됩니다.
- 프론트는 상대방 id만 body에 보내면 됩니다.
  - 아티스트 → 공간: `{ "space": <상대 공간 id>, "message": "..." }`
  - 공간 → 아티스트: `{ "artist": <상대 아티스트 id>, "message": "..." }`
""",
        request_body=SuggestionSerializer,
        responses={
            201: SuggestionSerializer,
            400: openapi.Response(
                description="유효성 오류",
                examples={
                    "application/json": {
                        "detail": "artist 또는 space 중 하나는 필수입니다.",
                        "code": "invalid_param",
                        "field": "receiver"
                    }
                }
            )
        },
        tags=["Suggestion"]
    )
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """
        sender는 토큰에서, receiver는 body에서 결정
        항상 artist/space 둘 다 serializer에 세팅
        """
        user = request.user
        role = getattr(user, "role", None)
        if role not in ("artist", "space"):
            return bad_request("role은 'artist' 또는 'space'여야 합니다.", "role")

        receiver_kind, receiver_obj, err = self._receiver_from_body(request.data)
        if err:
            return err

        data = request.data.copy()

        if role == "artist":
            my_artist = self._get_my_artist(user)
            if not my_artist:
                return bad_request("해당 유저의 Artist 프로필이 없습니다.", "artist")
            if receiver_kind != "space":
                return bad_request("아티스트는 공간에게만 제안할 수 있습니다.", "space")
            data["artist"] = my_artist.id
            data["space"] = receiver_obj.id

        else:  # role == "space"
            my_space = self._get_my_space(user)
            if not my_space:
                return bad_request("해당 유저의 Space 프로필이 없습니다.", "space")
            if receiver_kind != "artist":
                return bad_request("공간은 아티스트에게만 제안할 수 있습니다.", "artist")
            data["space"] = my_space.id
            data["artist"] = receiver_obj.id

        # 자기 자신에게 보내는 케이스 방지
        if role == "artist" and my_artist.user_id == receiver_obj.user_id:
            return bad_request("본인에게는 제안할 수 없습니다.", "receiver")
        if role == "space" and my_space.user_id == receiver_obj.user_id:
            return bad_request("본인에게는 제안할 수 없습니다.", "receiver")

        ser = self.get_serializer(data=data, context={"request": request})
        if not ser.is_valid():
            return bad_request(str(ser.errors))

        instance: Suggestion = ser.save()

        # 알림 (수신자에게)
        if instance.sender_type == Suggestion.SENDER_ARTIST:
            target_user = instance.space.user
            msg = f"{instance.artist.name} 아티스트가 {instance.space.place_name} 공간에 제안을 보냈습니다."
        else:
            target_user = instance.artist.user
            msg = f"{instance.space.place_name} 공간이 {instance.artist.name} 아티스트에게 제안을 보냈습니다."

        self._notify(
            user=target_user,
            content=msg,
            target_link=f"/api/v1/suggestions/{instance.id}/"
        )

        return Response(self.get_serializer(instance).data, status=status.HTTP_201_CREATED)
    @action(detail=True, methods=["patch"], url_path="accept")
    @transaction.atomic
    def accept(self, request, pk=None):
        """
        제안 수락 처리: 제안의 수신자만 수락 가능
        """
        suggestion = self.get_object()
        # 수신자 판별
        if suggestion.sender_type == Suggestion.SENDER_ARTIST:
            receiver_user_id = suggestion.space.user_id
        else:
            receiver_user_id = suggestion.artist.user_id

        if not request.user.is_superuser and request.user.id != receiver_user_id:
            return forbidden("제안 수신자만 수락할 수 있습니다.", "accept")

        if suggestion.is_accepted is not True:
            suggestion.is_accepted = True
            suggestion.save(update_fields=["is_accepted", "updated_at"])

            # 상대에게 알림
            if suggestion.sender_type == Suggestion.SENDER_ARTIST:
                target_user = suggestion.artist.user
            else:
                target_user = suggestion.space.user
            self._notify(
                user=target_user,
                content=f"'{suggestion}' 제안이 수락되었습니다.",
                target_link=f"/api/v1/suggestions/{suggestion.id}/"
            )

        return Response(self.get_serializer(suggestion).data, status=200)

    @action(detail=True, methods=["post"], url_path="read")
    @transaction.atomic
    def read(self, request, pk=None):
        """
        제안 읽음 처리: 제안의 수신자만 읽음 처리 가능
        """
        suggestion = self.get_object()
        # 수신자 판별
        if suggestion.sender_type == Suggestion.SENDER_ARTIST:
            receiver_user_id = suggestion.space.user_id
        else:
            receiver_user_id = suggestion.artist.user_id

        if not request.user.is_superuser and request.user.id != receiver_user_id:
            return forbidden("제안 수신자만 읽음 처리할 수 있습니다.", "read")

        if not suggestion.is_read:
            suggestion.is_read = True
            suggestion.save(update_fields=["is_read", "updated_at"])

        return Response({"id": suggestion.id, "is_read": True}, status=200)