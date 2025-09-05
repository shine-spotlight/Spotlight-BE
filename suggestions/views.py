from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Suggestion
from .serializers import SuggestionSerializer


class SuggestionViewSet(viewsets.ModelViewSet):
    queryset = Suggestion.objects.all().order_by("-created_at")
    serializer_class = SuggestionSerializer

    # ✅ 제안 생성
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        suggestion = serializer.save()
        return Response(self.get_serializer(suggestion).data, status=status.HTTP_201_CREATED)

    
        # ✅ 제안 수락 시 연락처 공개
    @action(detail=True, methods=["patch"])
    def accept(self, request, pk=None):
        suggestion = self.get_object()
        suggestion.is_accepted = True
        suggestion.save()

        data = self.get_serializer(suggestion).data

        # ✅ 연락처 공개: 아티스트 → 공간 / 공간 → 아티스트
        if suggestion.sender_type == "artist":
            data["receiver_phone"] = suggestion.space_id.user.phone_number
        else:
            data["receiver_phone"] = suggestion.artist_id.user.phone_number

        return Response(data, status=status.HTTP_200_OK)


    # ✅ 받은 제안 조회
    @action(detail=False, methods=["get"])
    def received(self, request):
        receiver_type = request.query_params.get("receiver_type")
        receiver_id = request.query_params.get("receiver_id")

        queryset = self.queryset
        if receiver_type == "artist":
            queryset = queryset.filter(artist_id__id=receiver_id)
        elif receiver_type == "space":
            queryset = queryset.filter(space_id__id=receiver_id)

        return Response(self.get_serializer(queryset, many=True).data, status=status.HTTP_200_OK)

    # ✅ 보낸 제안 조회
    @action(detail=False, methods=["get"])
    def sent(self, request):
        sender_type = request.query_params.get("sender_type")
        sender_id = request.query_params.get("sender_id")

        queryset = self.queryset
        if sender_type == "artist":
            queryset = queryset.filter(sender_type="artist", artist_id__id=sender_id)
        elif sender_type == "space":
            queryset = queryset.filter(sender_type="space", space_id__id=sender_id)

        return Response(self.get_serializer(queryset, many=True).data, status=status.HTTP_200_OK)
    @action(detail=True, methods=["patch"])
    def status(self, request, pk=None):
        suggestion = self.get_object()
        new_status = request.data.get("is_accepted")

        if new_status is None:
            return Response({"error": "is_accepted 값이 필요합니다."},
                            status=status.HTTP_400_BAD_REQUEST)

        suggestion.is_accepted = new_status
        suggestion.save()

        return Response(self.get_serializer(suggestion).data, status=status.HTTP_200_OK)