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
    artist_name = serializers.CharField(source="artist.name", read_only=True)
    space_name = serializers.CharField(source="space.place_name", read_only=True)

    receiver_phone = serializers.SerializerMethodField(read_only=True)
    opponent_image = serializers.SerializerMethodField(read_only=True)
    opponent_image_url = serializers.SerializerMethodField(read_only=True)  # 최대 길이 확장
    artist_obj = serializers.SerializerMethodField(read_only=True)
    space_obj = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Suggestion
        fields = [
            "id", "sender_type",
            "artist", "space",
            "artist_obj", "space_obj",
            "posting", "message",
            "is_free_allowed", "is_performed_confirmed",
            "is_accepted", "is_read",
            "receiver_phone", "opponent_image", "opponent_image_url",
            "created_at", "updated_at",
            "artist_name", "space_name"
        ]
        read_only_fields = [
            "id", "created_at", "updated_at",
            "artist_obj", "space_obj", "artist_name", "space_name", "opponent_image_url",
        ]

    def validate(self, attrs):
        request = self.context.get("request", None)
        if request and request.method == "PATCH":
            message = attrs.get("message", None)
            return attrs
        if request and request.method not in ("POST", "PUT", "PATCH"):
            return attrs

        message = attrs.get("message", "").strip()
        if not message:
            raise serializers.ValidationError({"message": "message는 필수입니다."})

        # 조건부 필드 검증 (self.instance가 있을 때만 sender_type 체크)
        is_free_allowed = attrs.get("is_free_allowed", getattr(self.instance, "is_free_allowed", None) if self.instance else None)
        is_performed_confirmed = attrs.get("is_performed_confirmed", getattr(self.instance, "is_performed_confirmed", None) if self.instance else None)
        if self.instance:
            sender_type = getattr(self.instance, "sender_type", None)
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
        원본 이미지 객체 (또는 상대방의 image 필드 값 그대로)
        """
        if obj.sender_type == Suggestion.SENDER_ARTIST and obj.space:
            images = getattr(obj.space, "place_image", None)
            if images:
                if hasattr(images, "all"):
                    first_img = images.first()
                    if first_img and hasattr(first_img, "image"):
                        return str(first_img.image)
                elif hasattr(images, "name"):
                    return str(images.name)
        elif obj.sender_type == Suggestion.SENDER_SPACE and obj.artist:
            return str(getattr(obj.artist.profile_image, "name", "")) or None
        return None

    def get_opponent_image_url(self, obj):
        """
        완전한 URL (http://.../media/...) 반환
        """
        request = self.context.get("request")
        if obj.sender_type == Suggestion.SENDER_ARTIST and obj.space:
            images = getattr(obj.space, "place_image", None)
            if images:
                if hasattr(images, "all"):
                    first_img = images.first()
                    if first_img and hasattr(first_img, "image") and first_img.image:
                        return request.build_absolute_uri(first_img.image.url)
                elif hasattr(images, "url"):
                    return request.build_absolute_uri(images.url)
        elif obj.sender_type == Suggestion.SENDER_SPACE and obj.artist:
            profile_image = getattr(obj.artist, "profile_image", None)
            if profile_image and hasattr(profile_image, "url"):
                return request.build_absolute_uri(profile_image.url)
        return None

    def get_artist_obj(self, obj):
        if obj.artist:
            return {"id": obj.artist.id, "name": obj.artist.name}
        return None

    def get_space_obj(self, obj):
        if obj.space:
            return {"id": obj.space.id, "place_name": obj.space.place_name}
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

class SuggestionPhoneShareSerializer(serializers.ModelSerializer):
    artist_phone = serializers.SerializerMethodField()
    space_phone = serializers.SerializerMethodField()

    class Meta:
        model = Suggestion
        fields = ["artist_phone", "space_phone"]

    def get_artist_phone(self, obj):
        artist_user = obj.artist.user if obj.artist else None
        return artist_user.phone_number if artist_user else None

    def get_space_phone(self, obj):
        space_user = obj.space.user if obj.space else None
        return space_user.phone_number if space_user else None