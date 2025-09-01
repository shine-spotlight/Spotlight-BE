from rest_framework import serializers
from .models import Like


class LikeSerializer(serializers.ModelSerializer):
    user_phone = serializers.CharField(source="user.phone_number", read_only=True)
    artist_name = serializers.CharField(source="artist.name", read_only=True)
    space_name = serializers.CharField(source="space.place_name", read_only=True)

    class Meta:
        model = Like
        fields = "__all__"
        read_only_fields = ["created_at", "user_phone", "artist_name", "space_name"]

    def validate(self, data):
        artist = data.get("artist")
        space = data.get("space")
        if artist and space:
            raise serializers.ValidationError("아티스트와 공간을 동시에 선택할 수 없습니다.")
        if not artist and not space:
            raise serializers.ValidationError("아티스트 또는 공간 중 하나를 선택해야 합니다.")
        return data
