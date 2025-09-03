from rest_framework import serializers
from .models import PointTransaction

class PointTransactionSerializer(serializers.ModelSerializer):
    user_phone = serializers.CharField(source="user.phone_number", read_only=True)
    balance = serializers.IntegerField(source="balance", read_only=True)

    class Meta:
        model = PointTransaction
        fields = [
            "id",
            "user",
            "transaction_type",
            "amount",
            "created_at",
            "user_phone",
            "balance",
        ]
        read_only_fields = ["id", "created_at", "balance"]
