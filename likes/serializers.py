from rest_framework import serializers
from .models import Like

class LikeSerializer(serializers.ModelSerializer):
    artist_name = serializers.CharField(source="artist.name", read_only=True)
    space_name = serializers.CharField(source="space.place_name", read_only=True)
    user_phone = serializers.CharField(source="user.phone_number", read_only=True)

    class Meta:
        model = Like
        fields = [
            "id",
            "user",
            "artist",
            "space",
            "artist_name",
            "space_name",
            "user_phone",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]
