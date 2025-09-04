from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import PointTransaction
from .serializers import PointTransactionSerializer

class PointViewSet(viewsets.ModelViewSet):  # ✅ config/urls.py 호환
    queryset = PointTransaction.objects.all().order_by("-created_at")
    serializer_class = PointTransactionSerializer

    @action(detail=False, methods=["get"])
    def history(self, request):
        user_id = request.query_params.get("user_id")
        if not user_id:
            return Response({"error": "user_id 필요"}, status=400)
        qs = self.queryset.filter(user__id=user_id)
        return Response(self.serializer_class(qs, many=True).data)

    @action(detail=False, methods=["get"])
    def balance(self, request):
        user_id = request.query_params.get("user_id")
        if not user_id:
            return Response({"error": "user_id 필요"}, status=400)
        latest = self.queryset.filter(user__id=user_id).last()
        balance = latest.balance if latest else 0
        return Response({"user_id": user_id, "balance": balance})

    @action(detail=False, methods=["post"])
    def charge(self, request):
        user_id = request.data.get("user")
        amount = request.data.get("amount")
        if not (user_id and amount):
            return Response({"error": "user, amount 필수"}, status=400)
        tx = PointTransaction.objects.create(user_id=user_id, transaction_type="charge", amount=amount)
        return Response(self.serializer_class(tx).data, status=201)

    @action(detail=False, methods=["post"])
    def deduct(self, request):
        user_id = request.data.get("user")
        amount = request.data.get("amount")
        if not (user_id and amount):
            return Response({"error": "user, amount 필수"}, status=400)
        tx = PointTransaction.objects.create(user_id=user_id, transaction_type="deduct", amount=amount)
        return Response(self.serializer_class(tx).data, status=201)
