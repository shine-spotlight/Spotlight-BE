from rest_framework import serializers
from .models import Like
from artists.models import Artist
from spaces.models import Space


# target_type, user_id은 프론트에서 받지 않고 자동 지정
class LikeSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    target_type = serializers.SerializerMethodField()
    target_id = serializers.SerializerMethodField()
    target_name = serializers.SerializerMethodField()

    class Meta:
        model = Like
        # user_id, target_type은 read_only로만 노출 (프론트 입력 불가)
        fields = ["id", "user_id", "target_type", "target_id", "target_name", "created_at"]
        read_only_fields = ["user_id", "target_type"]

    def create(self, validated_data):
        request = self.context.get("request")
        validated_data["user"] = request.user
        validated_data["target_type"] = "space" if getattr(request.user, "role", None) == "artist" else "artist"
        return super().create(validated_data)

    def get_target_type(self, obj):
        if obj.artist_id:
            return "artist"
        if obj.space_id:
            return "space"
        return None

    def get_target_id(self, obj):
        return obj.artist_id or obj.space_id

    def get_target_name(self, obj):
        if obj.artist:
            return obj.artist.name
        if obj.space:
            return obj.space.place_name
        return None
