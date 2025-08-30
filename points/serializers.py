from rest_framework import serializers
from .models import PointTransaction

class PointTransactionSerializer(serializers.ModelSerializer):
    balance = serializers.SerializerMethodField()

    class Meta:
        model = PointTransaction
        fields = '__all__'

    def get_balance(self, obj):
        return obj.balance
