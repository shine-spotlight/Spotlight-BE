from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Like
from .serializers import LikeSerializer

class LikeViewSet(viewsets.ModelViewSet):
    queryset = Like.objects.all()
    serializer_class = LikeSerializer

    # ✅ 특정 user의 좋아요 목록 확인
    @action(detail=False, methods=['get'])
    def user_likes(self, request):
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response({"error": "user_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        likes = Like.objects.filter(user_id=user_id)
        serializer = self.get_serializer(likes, many=True)
        return Response(serializer.data)

    # ✅ 토글 (한 번 더 누르면 좋아요 취소)
    @action(detail=False, methods=['post'])
    def toggle(self, request):
        user = request.data.get('user')
        target_type = request.data.get('target_type')
        target_id = request.data.get('target_id')

        if not (user and target_type and target_id):
            return Response({"error": "user, target_type, target_id required"}, status=status.HTTP_400_BAD_REQUEST)

        like = Like.objects.filter(user_id=user, target_type=target_type, target_id=target_id).first()

        if like:
            like.delete()
            return Response({"message": "Like removed"}, status=status.HTTP_200_OK)
        else:
            new_like = Like.objects.create(user_id=user, target_type=target_type, target_id=target_id)
            serializer = self.get_serializer(new_like)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
