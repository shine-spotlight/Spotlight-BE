from rest_framework import serializers
from .models import PointTransaction


class PointTransactionSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id", read_only=True)

    class Meta:
        model = PointTransaction
        fields = ["id", "user_id", "amount", "transaction_type", "created_at"]
        read_only_fields = ["id", "user_id", "transaction_type", "created_at"]
