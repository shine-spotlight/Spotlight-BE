from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import IntegrityError
from .models import Like
from .serializers import LikeSerializer


class LikeViewSet(viewsets.ModelViewSet):
    queryset = Like.objects.all().order_by("-created_at")
    serializer_class = LikeSerializer

    # ✅ 내가 찜한 목록 조회
    def list(self, request, *args, **kwargs):
        user_id = request.query_params.get("user_id")
        if not user_id:
            return Response({"error": "user_id 쿼리 파라미터가 필요합니다."}, status=400)

        queryset = self.queryset.filter(user__id=user_id)
        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data)

    # ✅ 아티스트 찜 토글
    @action(detail=False, methods=["post"], url_path="artists")
    def like_artist(self, request):
        user_id = request.data.get("user")
        artist_id = request.data.get("artist")

        if not (user_id and artist_id):
            return Response({"error": "user, artist 필수"}, status=400)

        existing = Like.objects.filter(user_id=user_id, artist_id=artist_id)
        if existing.exists():
            existing.delete()
            return Response({"liked": False}, status=200)

        try:
            like = Like.objects.create(user_id=user_id, artist_id=artist_id)
        except IntegrityError:
            return Response({"error": "이미 좋아요가 존재합니다."}, status=400)

        data = self.serializer_class(like).data
        data["liked"] = True
        return Response(data, status=201)

    # ✅ 공간 찜 토글
    @action(detail=False, methods=["post"], url_path="spaces")
    def like_space(self, request):
        user_id = request.data.get("user")
        space_id = request.data.get("space")

        if not (user_id and space_id):
            return Response({"error": "user, space 필수"}, status=400)

        existing = Like.objects.filter(user_id=user_id, space_id=space_id)
        if existing.exists():
            existing.delete()
            return Response({"liked": False}, status=200)

        try:
            like = Like.objects.create(user_id=user_id, space_id=space_id)
        except IntegrityError:
            return Response({"error": "이미 좋아요가 존재합니다."}, status=400)

        data = self.serializer_class(like).data
        data["liked"] = True
        return Response(data, status=201)
