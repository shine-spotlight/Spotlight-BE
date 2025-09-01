from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    user_phone = serializers.CharField(source="user.phone_number", read_only=True)

    class Meta:
        model = Notification
        fields = "__all__"
        read_only_fields = ["created_at", "user_phone", "is_read"]
