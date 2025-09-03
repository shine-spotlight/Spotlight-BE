from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import PointTransaction
from .serializers import PointTransactionSerializer


class PointTransactionViewSet(viewsets.ModelViewSet):
    queryset = PointTransaction.objects.all().order_by("-created_at")
    serializer_class = PointTransactionSerializer

    # GET /api/v1/points/history/?user_id=1
    @action(detail=False, methods=["get"])
    def history(self, request):
        user_id = request.query_params.get("user_id")
        if not user_id:
            return Response({"error": "user_id 필요"}, status=400)
        queryset = self.queryset.filter(user__id=user_id)
        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data)

    # GET /api/v1/points/balance/?user_id=1
    @action(detail=False, methods=["get"])
    def balance(self, request):
        user_id = request.query_params.get("user_id")
        if not user_id:
            return Response({"error": "user_id 필요"}, status=400)
        latest = self.queryset.filter(user__id=user_id).last()
        balance = latest.balance if latest else 0
        return Response({"user_id": user_id, "balance": balance})

    # POST /api/v1/points/charge/
    @action(detail=False, methods=["post"])
    def charge(self, request):
        user_id = request.data.get("user")
        amount = request.data.get("amount")
        if not (user_id and amount):
            return Response({"error": "user, amount 필수"}, status=400)
        tx = PointTransaction.objects.create(
            user_id=user_id, transaction_type="charge", amount=amount
        )
        return Response(self.serializer_class(tx).data, status=201)

    # POST /api/v1/points/deduct/
    @action(detail=False, methods=["post"])
    def deduct(self, request):
        user_id = request.data.get("user")
        amount = request.data.get("amount")
        if not (user_id and amount):
            return Response({"error": "user, amount 필수"}, status=400)
        tx = PointTransaction.objects.create(
            user_id=user_id, transaction_type="deduct", amount=amount
        )
        return Response(self.serializer_class(tx).data, status=201)


# ✅ config/urls.py 호환을 위해 alias 제공
PointViewSet = PointTransactionViewSet
