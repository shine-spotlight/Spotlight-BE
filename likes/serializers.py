from rest_framework import serializers
from .models import Like
from artists.models import Artist
from spaces.models import Space


class LikeSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    target_type = serializers.SerializerMethodField()
    target_id = serializers.SerializerMethodField()
    target_name = serializers.SerializerMethodField()

    class Meta:
        model = Like
        fields = ["id", "user_id", "target_type", "target_id", "target_name", "created_at"]

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
