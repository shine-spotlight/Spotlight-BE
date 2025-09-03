from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Like
from .serializers import LikeSerializer
from artists.models import Artist
from spaces.models import Space

class LikeViewSet(viewsets.ModelViewSet):
    queryset = Like.objects.all().order_by("-created_at")
    serializer_class = LikeSerializer

    # 내가 찜한 목록
    def list(self, request, *args, **kwargs):
        user_id = request.query_params.get("user_id")
        if not user_id:
            return Response({"error": "user_id 쿼리 파라미터가 필요합니다."}, status=400)
        queryset = self.queryset.filter(user__id=user_id)
        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data)

    # 아티스트 찜 등록
    @action(detail=False, methods=["post"], url_path="artists")
    def like_artist(self, request):
        user_id = request.data.get("user")
        artist_id = request.data.get("artist_id")
        if not (user_id and artist_id):
            return Response({"error": "user, artist_id 필수"}, status=400)
        like = Like.objects.create(user_id=user_id, artist_id=artist_id)
        return Response(self.serializer_class(like).data, status=201)

    # 공간 찜 등록
    @action(detail=False, methods=["post"], url_path="spaces")
    def like_space(self, request):
        user_id = request.data.get("user")
        space_id = request.data.get("space_id")
        if not (user_id and space_id):
            return Response({"error": "user, space_id 필수"}, status=400)
        like = Like.objects.create(user_id=user_id, space_id=space_id)
        return Response(self.serializer_class(like).data, status=201)
