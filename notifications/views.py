from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Notification
from .serializers import NotificationSerializer


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


class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all().order_by("-created_at")
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]   # ✅ 토큰 필수
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    # ✅ /api/v1/notifications/list/
    @swagger_auto_schema(
        operation_summary="내 알림 목록 조회",
        operation_description="현재 로그인한 사용자의 알림 목록을 조회합니다.",
        responses={200: NotificationSerializer(many=True)},
        tags=["Notification"]
    )
    def list(self, request):
        qs = self.queryset.filter(user=request.user)   # ✅ 무조건 본인만
        page = self.paginate_queryset(qs)
        ser = self.get_serializer(page or qs, many=True)
        if page is not None:
            return self.get_paginated_response(ser.data)
        return Response(ser.data, status=200)
    
    @swagger_auto_schema(
        operation_summary="알림 상세 조회",
        operation_description="특정 알림을 조회합니다. 본인 또는 관리자만 접근할 수 있습니다.",
        responses={200: NotificationSerializer, 403: "권한 없음", 404: "존재하지 않음"},
        tags=["Notification"]
    )
    def retrieve(self, request, *args, **kwargs):
        notif = self.get_object()
        if not request.user.is_staff and request.user != notif.user:
            return forbidden("본인 알림만 조회할 수 있습니다.", "notification_pk")
        ser = self.get_serializer(notif)
        return Response(ser.data, status=200)

    # ✅ 알림 읽음 처리
    @swagger_auto_schema(
        operation_summary="알림 읽음 처리",
        operation_description="특정 알림을 읽음 처리합니다.",
        responses={200: openapi.Response(description="읽음 처리 결과", examples={"application/json": {"id": 1, "is_read": True}})},
        tags=["Notification"]
    )
    def partial_update(self, request, pk=None):
        notif = self.get_object()
        if not request.user.is_staff and request.user != notif.user:
            return forbidden("본인 알림만 읽음 처리할 수 있습니다.", "notification_pk")

        notif.is_read = True
        notif.save(update_fields=["is_read"])
        return Response({"id": notif.id, "is_read": True}, status=200)

    # ✅ 알림 삭제
    @swagger_auto_schema(
        operation_summary="알림 삭제",
        operation_description="특정 알림을 삭제합니다.",
        responses={204: "삭제 성공", 403: "권한 없음"},
        tags=["Notification"]
    )
    def destroy(self, request, *args, **kwargs):
        notif = self.get_object()
        if not request.user.is_staff and request.user != notif.user:
            return forbidden("본인 알림만 삭제할 수 있습니다.", "notification_pk")
        notif.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @swagger_auto_schema(auto_schema=None) 
    def create(self, request, *args, **kwargs):
        pass