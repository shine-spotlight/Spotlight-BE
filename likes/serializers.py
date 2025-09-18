from rest_framework import serializers
from .models import Like
from artists.models import Artist
from spaces.models import Space


class LikeSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    target_type = serializers.SerializerMethodField()
    target_id = serializers.SerializerMethodField()
    target_name = serializers.SerializerMethodField()
    thumbnail = serializers.SerializerMethodField()
    address = serializers.SerializerMethodField()
    categories = serializers.SerializerMethodField()

    class Meta:
        model = Like
        fields = [
            "id", "user_id", "target_type", "target_id",
            "target_name", "thumbnail", "address", "categories", "created_at"
        ]
        read_only_fields = [
            "id", "user_id", "target_type", "target_id",
            "target_name", "thumbnail", "address", "categories", "created_at"
        ]

    def create(self, validated_data):
        request = self.context.get("request")
        role = getattr(request.user, "role", None)
        validated_data["user"] = request.user
        # 프론트는 상대 id만 보내므로, target_type은 role로 강제
        if role == "artist":
            validated_data["target_type"] = "space"
        elif role == "space":
            validated_data["target_type"] = "artist"
        else:
            raise serializers.ValidationError("role 정보가 필요합니다.")
        return super().create(validated_data)

    def get_target_type(self, obj):
        # GET 시에도 role 기반으로 target_type 반환
        request = self.context.get("request")
        role = getattr(request.user, "role", None) if request and hasattr(request, "user") else None
        if role == "artist":
            return "space"
        elif role == "space":
            return "artist"
        # fallback: 실제 객체 기반
        if obj.artist_id:
            return "artist"
        if obj.space_id:
            return "space"
        return None

    def get_target_id(self, obj):
        # role 기반으로 반환
        request = self.context.get("request")
        role = getattr(request.user, "role", None) if request and hasattr(request, "user") else None
        if role == "artist":
            return obj.space_id
        elif role == "space":
            return obj.artist_id
        return obj.artist_id or obj.space_id

    def get_target_name(self, obj):
        request = self.context.get("request")
        role = getattr(request.user, "role", None) if request and hasattr(request, "user") else None
        if role == "artist" and obj.space:
            return getattr(obj.space, "place_name", None)
        elif role == "space" and obj.artist:
            return getattr(obj.artist, "name", None)
        # fallback
        if obj.artist:
            return getattr(obj.artist, "name", None)
        if obj.space:
            return getattr(obj.space, "place_name", None)
        return None

    def get_thumbnail(self, obj):
        request = self.context.get("request")
        role = getattr(request.user, "role", None) if request and hasattr(request, "user") else None
        if role == "artist" and obj.space and hasattr(obj.space, "place_image"):
            images = obj.space.place_image
            if hasattr(images, "all"):
                first_img = images.first()
                if first_img and hasattr(first_img, "image") and first_img.image:
                    return first_img.image.url
            elif isinstance(images, (list, tuple)) and images:
                img = images[0]
                if hasattr(img, "image") and img.image:
                    return img.image.url
            elif hasattr(images, "url"):
                return images.url
        elif role == "space" and obj.artist and getattr(obj.artist, "profile_image", None):
            img = obj.artist.profile_image
            return img.url if hasattr(img, "url") else str(img)
        return None

    def get_address(self, obj):
        request = self.context.get("request")
        role = getattr(request.user, "role", None) if request and hasattr(request, "user") else None
        if role == "artist" and obj.space and hasattr(obj.space, "address"):
            return obj.space.address
        elif role == "space" and obj.artist and hasattr(obj.artist, "region"):
            return obj.artist.region
        return None

    def get_categories(self, obj):
        request = self.context.get("request")
        role = getattr(request.user, "role", None) if request and hasattr(request, "user") else None
        if role == "artist" and obj.space:
            return [c.name for c in getattr(obj.space, "categories", []).all()] if hasattr(obj.space, "categories") else []
        elif role == "space" and obj.artist:
            return [c.name for c in getattr(obj.artist, "categories", []).all()] if hasattr(obj.artist, "categories") else []
        # fallback
        if obj.artist and hasattr(obj.artist, "categories"):
            return [c.name for c in obj.artist.categories.all()]
        if obj.space and hasattr(obj.space, "categories"):
            return [c.name for c in obj.space.categories.all()]
        return []
