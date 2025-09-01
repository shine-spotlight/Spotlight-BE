from rest_framework import serializers
from .models import Like


class LikeSerializer(serializers.ModelSerializer):
    user_phone_number = serializers.CharField(
        source="user.phone_number", read_only=True
    )

    class Meta:
        model = Like
        fields = ["pk", "user", "user_phone_number", "target_type", "target_name", "created_at"]

    def validate(self, data):
        """
        중복 좋아요 방지
        """
        user = data.get("user")
        target_type = data.get("target_type")
        target_name = data.get("target_name")

        if Like.objects.filter(user=user, target_type=target_type, target_name=target_name).exists():
            raise serializers.ValidationError("이미 좋아요를 누르셨습니다.")

        return data
