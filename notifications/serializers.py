from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id", read_only=True)

    class Meta:
        model = Notification
        fields = ["id", "user_id", "content", "target_link", "is_read", "created_at"]
        read_only_fields = ["id", "user_id", "is_read", "created_at"]

    def validate_target_link(self, value):
        if value and not (value.startswith("http://") or value.startswith("https://")):
            raise serializers.ValidationError("target_link는 http:// 또는 https:// 이어야 합니다.")
        return value
