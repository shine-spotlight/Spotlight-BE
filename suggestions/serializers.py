from rest_framework import serializers
from .models import Suggestion
from artists.models import Artist
from spaces.models import Space
from artists.serializers import ArtistSerializer
from spaces.serializers import SpaceSerializer

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
    opponent_image = serializers.SerializerMethodField(read_only=True)  # 추가

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
            "opponent_image",  # 추가
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id", "sender_type", "artist_obj", "space_obj", "is_read", "receiver_phone", "opponent_image", "created_at", "updated_at"
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
        # 조회/리스트 등에서는 validate를 건너뜀
        request = self.context.get("request", None)
        if request and request.method == "PATCH":
            message = attrs.get("message", None)
            # PATCH에서는 artist, space가 없어도 됨 (부분 수정)
            return attrs
        if request and request.method not in ("POST", "PUT", "PATCH"):
            return attrs

        artist = attrs.get("artist", None)
        space = attrs.get("space", None)

        # 둘 다 없으면 에러 (둘 다 있으면 정상)
        if not artist or not space:
            raise serializers.ValidationError(
                {"detail": "artist와 space 모두 필요합니다."}
            )

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

    def get_opponent_image(self, obj):
        """
        상대방의 프로필 이미지를 반환:
        - sender_type이 artist면 상대는 space → space.place_image의 첫 번째 이미지
        - sender_type이 space면 상대는 artist → artist.profile_image
        """
        if obj.sender_type == Suggestion.SENDER_ARTIST and obj.space:
            # 공간의 place_image(다중) 중 첫 번째
            images = getattr(obj.space, "place_image", None)
            if images:
                # place_image가 ManyToMany나 related manager라면 .first() 사용
                if hasattr(images, "all"):
                    first_img = images.first()
                    if first_img and hasattr(first_img, "image") and first_img.image:
                        return first_img.image.url
                # place_image가 리스트라면
                elif isinstance(images, (list, tuple)) and images:
                    img = images[0]
                    if hasattr(img, "image") and img.image:
                        return img.image.url
            # place_image가 단일 필드라면
            if hasattr(images, "url"):
                return images.url
            return None
        elif obj.sender_type == Suggestion.SENDER_SPACE and obj.artist:
            # 아티스트의 profile_image
            profile_image = getattr(obj.artist, "profile_image", None)
            if profile_image:
                if hasattr(profile_image, "url"):
                    return profile_image.url
                return str(profile_image)
            return None
        return None

class SuggestionListSerializer(serializers.ModelSerializer):
    # 공간 주소
    space_address = serializers.CharField(source="space.address", read_only=True)
    # 공연 카테고리(아티스트)
    artist_categories = serializers.SerializerMethodField(read_only=True)
    # 공간 카테고리(스페이스)
    space_categories = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Suggestion
        fields = [
            "id", "message", "created_at", "is_read", "is_accepted",
            "space", "artist",
            "space_address", "artist_categories", "space_categories"
        ]

    def get_artist_categories(self, obj):
        if obj.artist:
            return [c.name for c in obj.artist.categories.all()]
        return []

    def get_space_categories(self, obj):
        if obj.space:
            return [c.name for c in obj.space.categories.all()]
        return []

# SuggestionViewSet에서 목록/상세 응답에 SuggestionListSerializer 사용