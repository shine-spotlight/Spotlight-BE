from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Like
from .serializers import LikeSerializer
from notifications.models import Notification


class LikeViewSet(viewsets.ModelViewSet):
    queryset = Like.objects.all().order_by("-created_at")
    serializer_class = LikeSerializer

    # 내가 찜한 목록 (artist_id, space_id 기준)
    def list(self, request, *args, **kwargs):
        user_id = request.query_params.get("user_id")
        if not user_id:
            return Response({"error": "user_id 쿼리 파라미터 필요"}, status=400)
        queryset = self.queryset.filter(user__id=user_id)
        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data)

    # 아티스트 좋아요 토글
    @action(detail=False, methods=["post"], url_path="artists")
    def like_artist(self, request):
        user_id = request.data.get("user_id")
        artist_id = request.data.get("artist_id")

        if not (user_id and artist_id):
            return Response({"error": "user_id, artist_id 필수"}, status=400)

        existing = Like.objects.filter(user_id=user_id, artist_id=artist_id)
        if existing.exists():
            existing.delete()
            return Response({"liked": False}, status=200)

        like = Like.objects.create(user_id=user_id, artist_id=artist_id)

        # 알림 생성
        Notification.objects.create(
            user=like.artist.user,
            content=f"{like.user.id}번 유저가 {like.artist.name}을(를) 찜했습니다.",
            target_link=f"http://127.0.0.1:8000/api/v1/artists/{like.artist.id}/"
        )

        data = self.serializer_class(like).data
        data["liked"] = True
        return Response(data, status=201)

    # 공간 좋아요 토글
    @action(detail=False, methods=["post"], url_path="spaces")
    def like_space(self, request):
        user_id = request.data.get("user_id")
        space_id = request.data.get("space_id")

        if not (user_id and space_id):
            return Response({"error": "user_id, space_id 필수"}, status=400)

        existing = Like.objects.filter(user_id=user_id, space_id=space_id)
        if existing.exists():
            existing.delete()
            return Response({"liked": False}, status=200)

        like = Like.objects.create(user_id=user_id, space_id=space_id)

        # 알림 생성
        Notification.objects.create(
            user=like.space.user,
            content=f"{like.user.id}번 유저가 {like.space.place_name}을(를) 찜했습니다.",
            target_link=f"http://127.0.0.1:8000/api/v1/spaces/{like.space.id}/"
        )

        data = self.serializer_class(like).data
        data["liked"] = True
        return Response(data, status=201)
