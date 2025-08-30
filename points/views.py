from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import PointTransaction
from .serializers import PointTransactionSerializer

class PointViewSet(viewsets.ModelViewSet):
    queryset = PointTransaction.objects.all().order_by('-created_at')
    serializer_class = PointTransactionSerializer

    @action(detail=True, methods=['get'])
    def balance(self, request, pk=None):
        user_transactions = PointTransaction.objects.filter(user_id=pk)
        if not user_transactions.exists():
            return Response({"balance": 0})
        last_tx = user_transactions.last()
        return Response({"balance": last_tx.balance})
