from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import PointTransaction
from .serializers import PointTransactionSerializer

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

    @swagger_auto_schema(
        operation_summary="포인트 내역 조회",
        operation_description="""
본인(아티스트) 또는 관리자만 포인트 거래 내역을 조회할 수 있습니다.

- 일반 유저(아티스트)는 쿼리 파라미터 없이 호출하면 본인 내역이 조회됩니다.
- 관리자는 user_id 쿼리 파라미터를 지정하면 해당 유저의 내역을 조회할 수 있습니다.
""",
        manual_parameters=[
            openapi.Parameter(
                'user_id',
                openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                description='조회할 유저 ID (관리자만 사용, 일반 유저는 생략)',
                required=False
            ),
        ],
        responses={200: PointTransactionSerializer(many=True)},
        tags=["Point"]
    )
    @action(detail=False, methods=["get"], url_path="history")
    def history(self, request):
        user_id = request.query_params.get("user_id")
        if not user_id:
            user_id = request.user.id

        if not request.user.is_superuser and str(request.user.id) != str(user_id):
            return forbidden("본인만 자신의 포인트 내역을 조회할 수 있습니다.", "user_id")

        qs = PointTransaction.objects.filter(user_id=user_id).order_by("-created_at")
        ser = PointTransactionSerializer(qs, many=True)
        return Response(ser.data, status=200)

    @swagger_auto_schema(
        operation_summary="포인트 잔액 조회",
        operation_description="""
본인(아티스트) 또는 관리자만 포인트 잔액을 조회할 수 있습니다.

- 일반 유저(아티스트)는 쿼리 파라미터 없이 호출하면 본인 잔액이 조회됩니다.
- 관리자는 user_id 쿼리 파라미터를 지정하면 해당 유저의 잔액을 조회할 수 있습니다.
""",
        manual_parameters=[
            openapi.Parameter(
                'user_id',
                openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                description='조회할 유저 ID (관리자만 사용, 일반 유저는 생략)',
                required=False
            ),
        ],
        responses={
            200: openapi.Response(
                description="포인트 잔액",
                examples={"application/json": {"user_id": 1, "balance": 10000}}
            )
        },
        tags=["Point"]
    )
    @action(detail=False, methods=["get"], url_path="balance")
    def balance(self, request):
        user_id = request.query_params.get("user_id")
        if not user_id:
            user_id = request.user.id

        if not request.user.is_superuser and str(request.user.id) != str(user_id):
            return forbidden("본인만 자신의 포인트 잔액을 조회할 수 있습니다.", "user_id")

        qs = PointTransaction.objects.filter(user_id=user_id).order_by("-created_at")
        balance = sum([tx.amount if tx.transaction_type == "charge" else -tx.amount for tx in qs])
        return Response({"user_id": int(user_id), "balance": balance}, status=200)

    @swagger_auto_schema(
        operation_summary="포인트 충전",
        operation_description="현재 로그인한 사용자의 포인트를 충전합니다.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'amount': openapi.Schema(type=openapi.TYPE_INTEGER, description="충전 금액 (필수)")
            },
            required=['amount']
        ),
        responses={201: PointTransactionSerializer},
        tags=["Point"]
    )
    @action(detail=False, methods=["post"], url_path="charge")
    @transaction.atomic
    def charge(self, request):
        amount = request.data.get("amount")

        if not amount:
            return bad_request("amount는 필수입니다.", "amount")

        tx = PointTransaction.objects.create(
            user=request.user,
            amount=int(amount),
            transaction_type="charge"
        )
        return Response(PointTransactionSerializer(tx).data, status=201)

    @swagger_auto_schema(
        operation_summary="포인트 차감",
        operation_description="현재 로그인한 사용자의 포인트를 차감합니다.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'amount': openapi.Schema(type=openapi.TYPE_INTEGER, description="차감 금액 (필수)")
            },
            required=['amount']
        ),
        responses={201: PointTransactionSerializer, 400: "잔액 부족"},
        tags=["Point"]
    )
    @action(detail=False, methods=["post"], url_path="deduct")
    @transaction.atomic
    def deduct(self, request):
        amount = request.data.get("amount")

        if not amount:
            return bad_request("amount는 필수입니다.", "amount")

        qs = PointTransaction.objects.filter(user=request.user).order_by("-created_at")
        balance = sum([tx.amount if tx.transaction_type == "charge" else -tx.amount for tx in qs])

        if balance < int(amount):
            return bad_request("잔액 부족으로 차감할 수 없습니다.", "amount")

        tx = PointTransaction.objects.create(
            user=request.user,
            amount=int(amount),
            transaction_type="deduct"
        )
        return Response(PointTransactionSerializer(tx).data, status=201)