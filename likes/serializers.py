from rest_framework import serializers
from .models import Like
from artists.models import Artist
from spaces.models import Space


class LikeSerializer(serializers.ModelSerializer):
    artist_name = serializers.CharField(source="artist.name", read_only=True)
    space_name = serializers.CharField(source="space.place_name", read_only=True)
    liked = serializers.SerializerMethodField()
    user_info = serializers.SerializerMethodField()  # ✅ 좋아요 누른 사람 요약

    class Meta:
        model = Like
        fields = [
            "id",
            "user",
            "user_info",     # ✅ user_id + nickname
            "artist",
            "space",
            "artist_name",
            "space_name",
            "liked",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "liked", "user_info"]

    def get_liked(self, obj):
        return True

    def get_user_info(self, obj):
        user_id = obj.user.id
        nickname = None

        if obj.user.role == "artist":
            artist = Artist.objects.filter(user=obj.user).first()
            if artist:
                nickname = artist.name
        elif obj.user.role == "space":
            space = Space.objects.filter(user=obj.user).first()
            if space:
                nickname = space.place_name

        return {
            "id": user_id,
            "nickname": nickname
        }
