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


# 공통 에러 포맷
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
    """
    개선 사항:
    - sender는 토큰(request.user)에서 자동 매핑
      • request.user.role == "artist"  → sender_type = artist, sender = 내 Artist 프로필
      • request.user.role == "space"   → sender_type = space,  sender = 내 Space 프로필
    - 프론트는 receiver만 전달 (artist 또는 space 중 하나 + message)
    - 받은함/보낸함 조회는 기본적으로 토큰 사용자 기준 (관리자는 쿼리로 특정 대상 조회 허용)
    """
    queryset = Suggestion.objects.all().order_by("-created_at")
    serializer_class = SuggestionSerializer
    permission_classes = [IsAuthenticated]

    # ----- 내부 유틸 -----
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
        artist_id = data.get("artist")
        space_id  = data.get("space")

        if artist_id and space_id:
            return None, None, bad_request("artist와 space 중 하나만 지정해야 합니다.", "receiver")

        if not artist_id and not space_id:
            return None, None, bad_request("receiver가 없습니다. artist 또는 space 중 하나는 필수입니다.", "receiver")

        if artist_id:
            try:
                artist = Artist.objects.get(pk=artist_id)
            except Artist.DoesNotExist:
                return None, None, bad_request("존재하지 않는 artist 입니다.", "artist")
            return "artist", artist, None

        if space_id:
            try:
                space = Space.objects.get(pk=space_id)
            except Space.DoesNotExist:
                return None, None, bad_request("존재하지 않는 space 입니다.", "space")
            return "space", space, None

        # 방어적
        return None, None, bad_request("receiver를 판별할 수 없습니다.", "receiver")

    def _notify(self, user, content, target_link):
        Notification.objects.create(
            user=user,
            content=content,
            target_link=target_link  # 예: "/api/v1/suggestions/123/"
        )

    # ----- 생성 -----
    
    @swagger_auto_schema(
        operation_summary="제안 목록 조회",
        operation_description="현재 로그인한 사용자의 제안 목록을 조회합니다.",
        responses={200: SuggestionSerializer(many=True)},
        tags=["Suggestion"]
    )
    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(qs)
        ser = self.get_serializer(page or qs, many=True)
        if page is not None:
            return self.get_paginated_response(ser.data)
        return Response(ser.data, status=200)

    @swagger_auto_schema(
        operation_summary="제안 상세 조회",
        operation_description="특정 제안을 상세 조회합니다.",
        responses={200: SuggestionSerializer, 404: "존재하지 않음"},
        tags=["Suggestion"]
    )
    def retrieve(self, request, *args, **kwargs):
        suggestion = self.get_object()
        ser = self.get_serializer(suggestion)
        return Response(ser.data, status=200)

    @swagger_auto_schema(
        operation_summary="제안 부분 수정",
        operation_description="특정 제안을 부분 수정합니다.",
        request_body=SuggestionSerializer,
        responses={200: SuggestionSerializer, 400: "유효성 오류"},
        tags=["Suggestion"]
    )
    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        ser = self.get_serializer(instance, data=request.data, partial=True)
        if ser.is_valid():
            ser.save()
            return Response(ser.data, status=200)
        return bad_request(str(ser.errors))

    @swagger_auto_schema(
        operation_summary="제안 삭제",
        operation_description="특정 제안을 삭제합니다.",
        responses={204: "삭제 성공", 403: "권한 없음"},
        tags=["Suggestion"]
    )
    def destroy(self, request, *args, **kwargs):
        suggestion = self.get_object()
        suggestion.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(auto_schema=None) 
    def update(self, request, *args, **kwargs):
        pass
    
    @swagger_auto_schema(
        operation_summary="제안 생성",
        operation_description="아티스트 또는 공간이 상대에게 제안을 생성합니다.",
        request_body=SuggestionSerializer,
        responses={201: SuggestionSerializer, 400: "유효성 오류"},
        tags=["Suggestion"]
    )
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """
        sender 자동 매핑:
          - user.role == "artist" → 내 Artist 프로필을 sender로 설정, body에는 space(수신자)만 필요
          - user.role == "space"  → 내 Space  프로필을 sender로 설정, body에는 artist(수신자)만 필요
        body 예:
          (아티스트 → 공간) { "space": 1, "message": "공연 제안합니다" }
          (공간 → 아티스트) { "artist": 2, "message": "제안드립니다" }
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
            # 보낼 수 있는 대상은 공간만
            if receiver_kind != "space":
                return bad_request("아티스트는 공간에게만 제안할 수 있습니다.", "space")
            # sender 자동 세팅
            data["sender_type"] = Suggestion.SENDER_ARTIST
            data["artist"] = my_artist.id
            data["space"] = receiver_obj.id

        else:  # role == "space"
            my_space = self._get_my_space(user)
            if not my_space:
                return bad_request("해당 유저의 Space 프로필이 없습니다.", "space")
            # 보낼 수 있는 대상은 아티스트만
            if receiver_kind != "artist":
                return bad_request("공간은 아티스트에게만 제안할 수 있습니다.", "artist")
            # sender 자동 세팅
            data["sender_type"] = Suggestion.SENDER_SPACE
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
            # 아티스트 → 공간
            target_user = instance.space.user
            msg = f"{instance.artist.name} 아티스트가 {instance.space.place_name} 공간에 제안을 보냈습니다."
        else:
            # 공간 → 아티스트
            target_user = instance.artist.user
            msg = f"{instance.space.place_name} 공간이 {instance.artist.name} 아티스트에게 제안을 보냈습니다."

        self._notify(
            user=target_user,
            content=msg,
            target_link=f"/api/v1/suggestions/{instance.id}/"
        )

        return Response(self.get_serializer(instance).data, status=status.HTTP_201_CREATED)

    # ----- 읽음 처리 -----
    @swagger_auto_schema(
        operation_summary="제안 읽음 처리",
        operation_description="제안 수신자가 해당 제안을 읽음 처리합니다.",
        responses={200: openapi.Response(description="읽음 처리 결과", examples={"application/json": {"id": 1, "is_read": True}})},
        tags=["Suggestion"]
    )
    @action(detail=True, methods=["post"], url_path="read")
    @transaction.atomic
    def read(self, request, pk=None):
        """
        제안서 '읽음' 처리. 제안 수신자만 가능.
        """
        sugg: Suggestion = self.get_object()
        # 수신자 판별
        receiver_user_id = (
            sugg.space.user_id if sugg.sender_type == Suggestion.SENDER_ARTIST else sugg.artist.user_id
        )
        if not request.user.is_superuser and request.user.id != receiver_user_id:
            return forbidden("제안 수신자만 읽음 처리할 수 있습니다.", "read")

        if not sugg.is_read:
            sugg.is_read = True
            sugg.save(update_fields=["is_read", "updated_at"])

        return Response({"id": sugg.id, "is_read": True}, status=200)

    # ----- 받은함 -----
    @swagger_auto_schema(
        operation_summary="받은 제안함 조회",
        operation_description="현재 로그인한 사용자의 받은 제안함을 조회합니다.",
        manual_parameters=[
            openapi.Parameter('receiver_type', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='수신자 타입(artist|space)', required=False),
            openapi.Parameter('receiver_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description='수신자 ID', required=False),
        ],
        responses={200: SuggestionSerializer(many=True)},
        tags=["Suggestion"]
    )
    @action(detail=False, methods=["get"], url_path="received")
    def received(self, request):
        """
        기본: 토큰 사용자 기준 받은 제안함을 반환.
        관리자만 receiver_type/receiver_id로 특정 대상의 받은함 조회 허용.
          - ?receiver_type=artist|space&receiver_id=<pk>
        """
        user = request.user
        qs = self.queryset

        r_type = request.query_params.get("receiver_type")
        r_id = request.query_params.get("receiver_id")

        if user.is_superuser and r_type in ("artist", "space") and r_id:
            # 관리자는 임의 조회 가능
            if r_type == "artist":
                try:
                    artist = Artist.objects.get(pk=r_id)
                except Artist.DoesNotExist:
                    return bad_request("존재하지 않는 artist 입니다.", "receiver_id")
                qs = qs.filter(artist=artist)
            else:
                try:
                    space = Space.objects.get(pk=r_id)
                except Space.DoesNotExist:
                    return bad_request("존재하지 않는 space 입니다.", "receiver_id")
                qs = qs.filter(space=space)
        else:
            # 일반 사용자는 자신의 프로필 기준만
            role = getattr(user, "role", None)
            if role == "artist":
                my_artist = self._get_my_artist(user)
                if not my_artist:
                    return bad_request("해당 유저의 Artist 프로필이 없습니다.", "artist")
                qs = qs.filter(artist=my_artist)
            elif role == "space":
                my_space = self._get_my_space(user)
                if not my_space:
                    return bad_request("해당 유저의 Space 프로필이 없습니다.", "space")
                qs = qs.filter(space=my_space)
            else:
                return bad_request("role은 'artist' 또는 'space'여야 합니다.", "role")

        page = self.paginate_queryset(qs.order_by("-created_at"))
        ser = self.get_serializer(page or qs, many=True)
        if page is not None:
            return self.get_paginated_response(ser.data)
        return Response(ser.data, status=200)

    # ----- 보낸함 -----
    @swagger_auto_schema(
        operation_summary="보낸 제안함 조회",
        operation_description="현재 로그인한 사용자의 보낸 제안함을 조회합니다.",
        manual_parameters=[
            openapi.Parameter('sender_type', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='발신자 타입(artist|space)', required=False),
            openapi.Parameter('sender_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description='발신자 ID', required=False),
        ],
        responses={200: SuggestionSerializer(many=True)},
        tags=["Suggestion"]
    )
    @action(detail=False, methods=["get"], url_path="sent")
    def sent(self, request):
        """
        기본: 토큰 사용자 기준 보낸 제안함을 반환.
        관리자만 sender_type/sender_id로 특정 발신자의 보낸함 조회 허용.
          - ?sender_type=artist|space&sender_id=<pk>
        """
        user = request.user
        qs = self.queryset

        s_type = request.query_params.get("sender_type")
        s_id = request.query_params.get("sender_id")

        if user.is_superuser and s_type in ("artist", "space") and s_id:
            if s_type == "artist":
                try:
                    artist = Artist.objects.get(pk=s_id)
                except Artist.DoesNotExist:
                    return bad_request("존재하지 않는 artist 입니다.", "sender_id")
                qs = qs.filter(sender_type=Suggestion.SENDER_ARTIST, artist=artist)
            else:
                try:
                    space = Space.objects.get(pk=s_id)
                except Space.DoesNotExist:
                    return bad_request("존재하지 않는 space 입니다.", "sender_id")
                qs = qs.filter(sender_type=Suggestion.SENDER_SPACE, space=space)
        else:
            role = getattr(user, "role", None)
            if role == "artist":
                my_artist = self._get_my_artist(user)
                if not my_artist:
                    return bad_request("해당 유저의 Artist 프로필이 없습니다.", "artist")
                qs = qs.filter(sender_type=Suggestion.SENDER_ARTIST, artist=my_artist)
            elif role == "space":
                my_space = self._get_my_space(user)
                if not my_space:
                    return bad_request("해당 유저의 Space 프로필이 없습니다.", "space")
                qs = qs.filter(sender_type=Suggestion.SENDER_SPACE, space=my_space)
            else:
                return bad_request("role은 'artist' 또는 'space'여야 합니다.", "role")

        page = self.paginate_queryset(qs.order_by("-created_at"))
        ser = self.get_serializer(page or qs, many=True)
        if page is not None:
            return self.get_paginated_response(ser.data)
        return Response(ser.data, status=200)

    # ----- 수락 처리 -----
    @swagger_auto_schema(
        operation_summary="제안 수락 처리",
        operation_description="제안 수신자가 해당 제안을 수락 처리합니다.",
        responses={200: SuggestionSerializer},
        tags=["Suggestion"]
    )
    @action(detail=True, methods=["patch"], url_path="accept")
    @transaction.atomic
    def accept(self, request, pk=None):
        """
        제안 수신자만 수락 가능.
        수락 시 상대에게 알림 발송.
        """
        sugg: Suggestion = self.get_object()
        receiver_user_id = (
            sugg.space.user_id if sugg.sender_type == Suggestion.SENDER_ARTIST else sugg.artist.user_id
        )
        if not request.user.is_superuser and request.user.id != receiver_user_id:
            return forbidden("제안 수신자만 수락할 수 있습니다.", "accept")

        if sugg.is_accepted is not True:
            sugg.is_accepted = True
            sugg.save(update_fields=["is_accepted", "updated_at"])

            # 상대에게 알림
            target_user = sugg.artist.user if sugg.sender_type == Suggestion.SENDER_SPACE else sugg.space.user
            self._notify(
                user=target_user,
                content=f"'{sugg}' 제안이 수락되었습니다.",
                target_link=f"/api/v1/suggestions/{sugg.id}/"
            )

        return Response(self.get_serializer(sugg).data, status=200)