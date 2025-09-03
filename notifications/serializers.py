from rest_framework import serializers
from .models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    user_phone = serializers.CharField(source="user.phone_number", read_only=True)

    class Meta:
        model = Notification
        fields = [
            "id",
            "user",
            "content",
            "target_link",
            "is_read",
            "created_at",
            "user_phone",
        ]
        read_only_fields = ["id", "created_at"]
