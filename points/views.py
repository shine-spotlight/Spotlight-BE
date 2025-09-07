from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import PointTransaction
from .serializers import PointTransactionSerializer
from users.models import User


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


class PointViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get"], url_path="history")
    def history(self, request):
        user_id = request.query_params.get("user_id")
        if not user_id:
            return bad_request("user_id는 필수입니다.", "user_id")

        if not request.user.is_superuser and str(request.user.id) != str(user_id):
            return forbidden("본인만 자신의 포인트 내역을 조회할 수 있습니다.", "user_id")

        qs = PointTransaction.objects.filter(user_id=user_id).order_by("-created_at")
        ser = PointTransactionSerializer(qs, many=True)
        return Response(ser.data, status=200)

    @action(detail=False, methods=["get"], url_path="balance")
    def balance(self, request):
        user_id = request.query_params.get("user_id")
        if not user_id:
            return bad_request("user_id는 필수입니다.", "user_id")

        if not request.user.is_superuser and str(request.user.id) != str(user_id):
            return forbidden("본인만 자신의 포인트 잔액을 조회할 수 있습니다.", "user_id")

        qs = PointTransaction.objects.filter(user_id=user_id).order_by("-created_at")
        balance = sum([tx.amount if tx.transaction_type == "charge" else -tx.amount for tx in qs])
        return Response({"user_id": int(user_id), "balance": balance}, status=200)

    @action(detail=False, methods=["post"], url_path="charge")
    @transaction.atomic
    def charge(self, request):
        user_id = request.data.get("user")
        amount = request.data.get("amount")

        if not user_id:
            return bad_request("user는 필수입니다.", "user")
        if not amount:
            return bad_request("amount는 필수입니다.", "amount")

        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return bad_request("존재하지 않는 user_id 입니다.", "user")

        tx = PointTransaction.objects.create(
            user=user,
            amount=int(amount),
            transaction_type="charge"
        )
        return Response(PointTransactionSerializer(tx).data, status=201)

    @action(detail=False, methods=["post"], url_path="deduct")
    @transaction.atomic
    def deduct(self, request):
        user_id = request.data.get("user")
        amount = request.data.get("amount")

        if not user_id:
            return bad_request("user는 필수입니다.", "user")
        if not amount:
            return bad_request("amount는 필수입니다.", "amount")

        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return bad_request("존재하지 않는 user_id 입니다.", "user")

        # 현재 잔액 확인
        qs = PointTransaction.objects.filter(user=user).order_by("-created_at")
        balance = sum([tx.amount if tx.transaction_type == "charge" else -tx.amount for tx in qs])

        if balance < int(amount):
            return bad_request("잔액 부족으로 차감할 수 없습니다.", "amount")

        tx = PointTransaction.objects.create(
            user=user,
            amount=int(amount),
            transaction_type="deduct"
        )
        return Response(PointTransactionSerializer(tx).data, status=201)
