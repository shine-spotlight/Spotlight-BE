from rest_framework import serializers
from .models import Suggestion
from artists.models import Artist
from spaces.models import Space

class SuggestionSerializer(serializers.ModelSerializer):
    artist = serializers.PrimaryKeyRelatedField(
        queryset=Artist.objects.all(), write_only=True, required=False, allow_null=True
    )
    space = serializers.PrimaryKeyRelatedField(
        queryset=Space.objects.all(), write_only=True, required=False, allow_null=True
    )
    artist_obj = serializers.SerializerMethodField(read_only=True)
    space_obj = serializers.SerializerMethodField(read_only=True)
    receiver_phone = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Suggestion
        fields = [
            "id",
            "sender_type",
            "artist", "space",
            "artist_obj", "space_obj",
            "posting",
            "message",
            "is_free_allowed",
            "is_performed_confirmed",
            "is_accepted",
            "is_read",
            "receiver_phone",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id", "sender_type", "artist_obj", "space_obj", "is_read", "receiver_phone", "created_at", "updated_at"
        ]

    def get_artist_obj(self, obj):
        if obj.artist:
            return {
                "id": obj.artist.id,
                "name": getattr(obj.artist, "name", None)
            }
        return None

    def get_space_obj(self, obj):
        if obj.space:
            return {
                "id": obj.space.id,
                "place_name": getattr(obj.space, "place_name", None)
            }
        return None

    def validate(self, attrs):
        artist = attrs.get("artist", None)
        space = attrs.get("space", None)

        # 동시에 들어오면 막기
        if artist and space:
            raise serializers.ValidationError(
                {"detail": "artist와 space는 동시에 입력할 수 없습니다."}
            )

        # 여기서는 "하나도 없으면 안 된다" 체크 제거
        # SuggestionViewSet.create()에서 role 기반으로 채워줌

        # 메시지 필수
        message = attrs.get("message", "").strip()
        if not message:
            raise serializers.ValidationError({"message": "message는 필수입니다."})

        # 조건부 필드 검증 (기존 그대로 유지)
        is_free_allowed = attrs.get("is_free_allowed", getattr(self.instance, "is_free_allowed", None) if self.instance else None)
        is_performed_confirmed = attrs.get("is_performed_confirmed", getattr(self.instance, "is_performed_confirmed", None) if self.instance else None)
        sender_type = getattr(self.instance, "sender_type", None) if self.instance else None
        if sender_type == Suggestion.SENDER_ARTIST and is_performed_confirmed is not None:
            raise serializers.ValidationError({"is_performed_confirmed": "artist 발신에서는 허용되지 않습니다."})
        if sender_type == Suggestion.SENDER_SPACE and is_free_allowed is not None:
            raise serializers.ValidationError({"is_free_allowed": "space 발신에서는 허용되지 않습니다."})

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