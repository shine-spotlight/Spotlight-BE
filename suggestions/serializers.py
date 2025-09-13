from rest_framework import serializers
from .models import Suggestion
from artists.models import Artist
from spaces.models import Space


class SuggestionSerializer(serializers.ModelSerializer):
    # write: *_id, read: FK id 노출
    artist_id = serializers.PrimaryKeyRelatedField(
        queryset=Artist.objects.all(), source="artist", write_only=True, required=False
    )
    space_id = serializers.PrimaryKeyRelatedField(
        queryset=Space.objects.all(), source="space", write_only=True, required=False
    )

    # 수락 후에만 공개되는 상대방 연락처
    receiver_phone = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Suggestion
        fields = [
            "id",
            "sender_type",
            "artist", "artist_id",
            "space", "space_id",
            "posting",
            "message",
            "is_free_allowed",
            "is_performed_confirmed",
            "is_accepted",
            "receiver_phone",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "sender_type", "artist", "space", "receiver_phone", "created_at", "updated_at"]

    def validate(self, attrs):
        sender_type = attrs.get("sender_type") or getattr(self.instance, "sender_type", None)
        artist = attrs.get("artist") or getattr(self.instance, "artist", None)
        space = attrs.get("space") or getattr(self.instance, "space", None)

        if sender_type not in (Suggestion.SENDER_ARTIST, Suggestion.SENDER_SPACE, None):
            raise serializers.ValidationError({"sender_type": "sender_type는 'artist' 또는 'space'여야 합니다."})

        # 양쪽 FK 필수
        if not artist and not space:
            raise serializers.ValidationError({"detail": "artist_id와 space_id는 모두 필요합니다."})

        # 조건부 필드 허용 범위
        is_free_allowed = attrs.get("is_free_allowed", getattr(self.instance, "is_free_allowed", None))
        is_performed_confirmed = attrs.get("is_performed_confirmed", getattr(self.instance, "is_performed_confirmed", None))

        if sender_type == Suggestion.SENDER_ARTIST:
            if is_performed_confirmed is not None:
                raise serializers.ValidationError({"is_performed_confirmed": "artist 발신에서는 허용되지 않습니다."})
        if sender_type == Suggestion.SENDER_SPACE:
            if is_free_allowed is not None:
                raise serializers.ValidationError({"is_free_allowed": "space 발신에서는 허용되지 않습니다."})

        # 메시지 필수
        message = attrs.get("message", "").strip() or getattr(self.instance, "message", "").strip()
        if not message:
            raise serializers.ValidationError({"message": "message는 필수입니다."})

        return attrs

    def get_receiver_phone(self, obj: Suggestion):
        """
        수락 전에는 절대 노출하지 않음.
        수락 후: 요청자 기준 '상대방'의 users.phone_number를 반환.
        """
        request = self.context.get("request")
        if not obj.is_accepted:
            return None
        if not request or not request.user or not request.user.is_authenticated:
            return None

        # 요청자가 아티스트 유저면 -> 공간 보유자 전화, 반대면 -> 아티스트 유저 전화
        try:
            artist_user_id = obj.artist.user_id
            space_user_id = obj.space.user_id
        except AttributeError:
            return None

        if request.user.id == artist_user_id:
            return obj.space.user.phone_number
        if request.user.id == space_user_id:
            return obj.artist.user.phone_number
        # 제3자면 노출 X
        return None
