from rest_framework import serializers
from .models import Suggestion

class SuggestionSerializer(serializers.ModelSerializer):
    artist_name = serializers.CharField(source="artist_id.name", read_only=True)
    space_name = serializers.CharField(source="space_id.place_name", read_only=True)

    class Meta:
        model = Suggestion
        fields = "__all__"
        read_only_fields = ["created_at", "artist_name", "space_name"]

    def update(self, instance, validated_data):
        user = self.context["request"].user

        # 아티스트만 is_free_allowed 수정 가능
        if "is_free_allowed" in validated_data and user.role != "artist":
            raise serializers.ValidationError("아티스트만 무료 공연 여부를 수정할 수 있습니다.")

        # 공간만 is_performed_confirmed 수정 가능
        if "is_performed_confirmed" in validated_data and user.role != "space":
            raise serializers.ValidationError("공간 보유자만 공연 완료 확인을 할 수 있습니다.")

        return super().update(instance, validated_data)
