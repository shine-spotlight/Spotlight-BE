from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Posting
from .serializers import PostingSerializer

class PostingViewSet(viewsets.ModelViewSet):
    queryset = Posting.objects.all().order_by("-created_at")
    serializer_class = PostingSerializer

    # GET /api/v1/postings/filter/
    @action(detail=False, methods=["get"])
    def filter(self, request):
        queryset = self.queryset
        category = request.query_params.get("category")
        date = request.query_params.get("date")
        region = request.query_params.get("region")

        if category:
            queryset = queryset.filter(categories__name__icontains=category)
        if date:
            queryset = queryset.filter(date=date)
        if region:
            queryset = queryset.filter(space__place_region__icontains=region)

        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # POST /api/v1/postings/{pk}/suggestion/
    @action(detail=True, methods=["post"])
    def suggestion(self, request, pk=None):
        posting = self.get_object()
        message = request.data.get("message")
        if not message:
            return Response({"error": "message is required"}, status=status.HTTP_400_BAD_REQUEST)

        # 여기서는 실제 Suggestion 모델과 연결해야 함
        # 지금은 placeholder로 응답만 반환
        return Response(
            {
                "posting": posting.id,
                "space": posting.space.id if posting.space else None,
                "message": message,
                "status": "suggestion created (stub)"
            },
            status=status.HTTP_201_CREATED,
        )
