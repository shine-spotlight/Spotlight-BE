from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import Like
from .serializers import LikeSerializer


class LikeViewSet(viewsets.ModelViewSet):
    queryset = Like.objects.all()
    serializer_class = LikeSerializer

    def create(self, request, *args, **kwargs):
        user = request.user
        artist = request.data.get("artist")
        space = request.data.get("space")

        # 아티스트 좋아요 → 토글
        if artist and Like.objects.filter(user=user, artist_id=artist).exists():
            Like.objects.filter(user=user, artist_id=artist).delete()
            return Response({"detail": "아티스트 좋아요가 취소되었습니다."}, status=status.HTTP_200_OK)

        # 공간 좋아요 → 토글
        if space and Like.objects.filter(user=user, space_id=space).exists():
            Like.objects.filter(user=user, space_id=space).delete()
            return Response({"detail": "공간 좋아요가 취소되었습니다."}, status=status.HTTP_200_OK)

        return super().create(request, *args, **kwargs)
