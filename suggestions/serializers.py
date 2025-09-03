from rest_framework import serializers
from .models import Suggestion
from artists.models import Artist
from spaces.models import Space

class SuggestionSerializer(serializers.ModelSerializer):
    artist_name = serializers.CharField(source="artist_id.name", read_only=True)
    space_name = serializers.CharField(source="space_id.place_name", read_only=True)
    artist_phone = serializers.CharField(source="artist_id.user.phone_number", read_only=True)
    space_phone = serializers.CharField(source="space_id.user.phone_number", read_only=True)

    class Meta:
        model = Suggestion
        fields = [
            "id",
            "sender_type",
            "artist_id",
            "space_id",
            "message",
            "is_accepted",
            "is_free_allowed",
            "is_performed_confirmed",
            "artist_name",
            "space_name",
            "artist_phone",
            "space_phone",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]
