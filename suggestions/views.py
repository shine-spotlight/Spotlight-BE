from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import models

from .models import Suggestion
from .serializers import SuggestionSerializer, SuggestionListSerializer
from artists.models import Artist
from spaces.models import Space
from notifications.models import Notification
from points.models import PointTransaction

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

    @swagger_auto_schema(
        operation_summary="받은 제안함",
        operation_description="내 artist/space 프로필 기준으로 받은 제안만 반환합니다.",
        tags=["Suggestion"]
    )
    @action(detail=False, methods=["get"], url_path="received")
    def received(self, request):
        """내가 받은 제안서만 반환"""
        user = request.user
        qs = self.get_queryset().filter(
            (models.Q(sender_type=Suggestion.SENDER_ARTIST, space__user=user) |
             models.Q(sender_type=Suggestion.SENDER_SPACE, artist__user=user))
        )
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = SuggestionListSerializer(page, many=True, context={"request": request})
            data = serializer.data
            # artist_obj, space_obj, opponent_image 추가
            for idx, obj in enumerate(page):
                data[idx]["artist_obj"] = SuggestionSerializer(obj, context={"request": request}).get_artist_obj(obj)
                data[idx]["space_obj"] = SuggestionSerializer(obj, context={"request": request}).get_space_obj(obj)
                data[idx]["opponent_image"] = SuggestionSerializer(obj, context={"request": request}).get_opponent_image(obj)
            return self.get_paginated_response(data)
        serializer = SuggestionListSerializer(qs, many=True, context={"request": request})
        data = serializer.data
        for idx, obj in enumerate(qs):
            data[idx]["artist_obj"] = SuggestionSerializer(obj, context={"request": request}).get_artist_obj(obj)
            data[idx]["space_obj"] = SuggestionSerializer(obj, context={"request": request}).get_space_obj(obj)
            data[idx]["opponent_image"] = SuggestionSerializer(obj, context={"request": request}).get_opponent_image(obj)
        return Response(data)

    @swagger_auto_schema(
        operation_summary="보낸 제안함",
        operation_description="내 artist/space 프로필 기준으로 보낸 제안만 반환합니다.",
        tags=["Suggestion"]
    )
    @action(detail=False, methods=["get"], url_path="sent")
    def sent(self, request):
        """내가 보낸 제안서만 반환"""
        user = request.user
        qs = self.get_queryset().filter(
            (models.Q(sender_type=Suggestion.SENDER_ARTIST, artist__user=user) |
             models.Q(sender_type=Suggestion.SENDER_SPACE, space__user=user))
        )
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = SuggestionListSerializer(page, many=True, context={"request": request})
            data = serializer.data
            for idx, obj in enumerate(page):
                data[idx]["artist_obj"] = SuggestionSerializer(obj, context={"request": request}).get_artist_obj(obj)
                data[idx]["space_obj"] = SuggestionSerializer(obj, context={"request": request}).get_space_obj(obj)
            return self.get_paginated_response(data)
        serializer = SuggestionListSerializer(qs, many=True, context={"request": request})
        data = serializer.data
        for idx, obj in enumerate(qs):
            data[idx]["artist_obj"] = SuggestionSerializer(obj, context={"request": request}).get_artist_obj(obj)
            data[idx]["space_obj"] = SuggestionSerializer(obj, context={"request": request}).get_space_obj(obj)
        return Response(data)

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

- 프론트는 '상대방 id'만 body에 보내면 됩니다.
  - 아티스트 → 공간: `{ "space": <상대 공간 id>, "message": "..." }`
  - 공간 → 아티스트: `{ "artist": <상대 아티스트 id>, "message": "..." }`
- 본인 프로필(artist/space)은 토큰에서 자동 매핑됩니다.
- sender_type은 서버에서 자동 지정되어 응답에만 포함됩니다.

**사진 관련 안내**
- 응답 데이터의 `opponent_image` 필드는 상대방의 대표 이미지를 제공합니다.
    - 상대가 아티스트면 `artist.profile_image`의 URL이 반환됩니다.
    - 상대가 공간이면 `space.place_image`의 첫 번째 이미지 URL이 반환됩니다.
- `artist_obj`, `space_obj` 필드로도 상대방의 id/이름(공간명) 정보를 확인할 수 있습니다.

**중요**
- 프론트는 내 role(artist/space)에 따라 상대방 id만 body에 포함하면 됩니다.
- sender_type, 내 프로필 id 등은 절대 body에 넣지 마세요. 서버에서 자동 처리합니다.
""",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'artist': openapi.Schema(type=openapi.TYPE_INTEGER, description="상대 아티스트 id (space→artist일 때만)"),
                'space': openapi.Schema(type=openapi.TYPE_INTEGER, description="상대 공간 id (artist→space일 때만)"),
                'message': openapi.Schema(type=openapi.TYPE_STRING, description="제안 메시지")
            },
            required=['message']
        ),
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
        user = request.user
        role = getattr(user, "role", None)
        if role not in ("artist", "space"):
            return bad_request("role은 'artist' 또는 'space'여야 합니다.", "role")

        data = request.data.copy()

        # role 기반 분기에서만 상대방 매핑
        if role == "artist":
            my_artist = self._get_my_artist(user)
            if not my_artist:
                return bad_request("해당 유저의 Artist 프로필이 없습니다.", "artist")
            space_id = data.get("space")
            if not space_id:
                return bad_request("상대 공간 id(space)는 필수입니다.", "space")
            data["artist"] = my_artist.id
            data["sender_type"] = Suggestion.SENDER_ARTIST
            receiver_obj = Space.objects.filter(pk=space_id).first()
            if not receiver_obj:
                return bad_request("존재하지 않는 space 입니다.", "space")
            if my_artist.user_id == receiver_obj.user_id:
                return bad_request("본인에게는 제안할 수 없습니다.", "receiver")
            # ✅ 아티스트만 포인트 잔액 검사
            balance = sum([
                tx.amount if tx.transaction_type == "charge" else -tx.amount
                for tx in PointTransaction.objects.filter(user=user)
            ])
            if balance < 1000:
                return bad_request("포인트가 부족합니다.", "point")
        elif role == "space":
            my_space = self._get_my_space(user)
            if not my_space:
                return bad_request("해당 유저의 Space 프로필이 없습니다.", "space")
            artist_id = data.get("artist")
            if not artist_id:
                return bad_request("상대 아티스트 id(artist)는 필수입니다.", "artist")
            data["space"] = my_space.id
            data["sender_type"] = Suggestion.SENDER_SPACE
            receiver_obj = Artist.objects.filter(pk=artist_id).first()
            if not receiver_obj:
                return bad_request("존재하지 않는 artist 입니다.", "artist")
            if my_space.user_id == receiver_obj.user_id:
                return bad_request("본인에게는 제안할 수 없습니다.", "receiver")

        # 중복 체크
        exists = Suggestion.objects.filter(artist_id=data["artist"], space_id=data["space"]).exists()
        if exists:
            return bad_request("이미 동일한 artist/space 조합의 제안이 존재합니다.", "artist/space")

        ser = self.get_serializer(data=data, context={"request": request})
        if not ser.is_valid():
            return bad_request(str(ser.errors))
        instance: Suggestion = ser.save()

        # 포인트 차감: 아티스트가 보낼 때만 차감
        if instance.sender_type == Suggestion.SENDER_ARTIST:
            PointTransaction.objects.create(
                user=user,
                amount=1000,
                transaction_type="deduct"
            )

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

    @swagger_auto_schema(
        operation_summary="제안 수락 처리",
        operation_description="""
제안의 수신자(공간 또는 아티스트)만 해당 제안을 수락할 수 있습니다.

- 아티스트가 보낸 제안: 공간 소유자만 수락 가능
- 공간이 보낸 제안: 아티스트 본인만 수락 가능
- 이미 수락된 제안은 다시 수락할 수 없습니다.
""",
        responses={
            200: SuggestionSerializer,
            403: openapi.Response(
                description="권한 없음",
                examples={
                    "application/json": {
                        "detail": "제안 수신자만 수락할 수 있습니다.",
                        "code": "permission_denied",
                        "field": "accept"
                    }
                }
            )
        },
        tags=["Suggestion"]
    )
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

    @swagger_auto_schema(
        operation_summary="제안 읽음 처리",
        operation_description="""
제안의 수신자(공간 또는 아티스트)만 해당 제안을 읽음 처리할 수 있습니다.

- 아티스트가 보낸 제안: 공간 소유자만 읽음 처리 가능
- 공간이 보낸 제안: 아티스트 본인만 읽음 처리 가능
- 이미 읽음 처리된 제안은 다시 처리하지 않습니다.
""",
        responses={
            200: openapi.Response(
                description="읽음 처리 결과",
                examples={"application/json": {"id": 1, "is_read": True}}
            ),
            403: openapi.Response(
                description="권한 없음",
                examples={
                    "application/json": {
                        "detail": "제안 수신자만 읽음 처리할 수 있습니다.",
                        "code": "permission_denied",
                        "field": "read"
                    }
                }
            )
        },
        tags=["Suggestion"]
    )
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