from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Suggestion
from .serializers import SuggestionSerializer

class SuggestionViewSet(viewsets.ModelViewSet):
    queryset = Suggestion.objects.all().order_by("-created_at")
    serializer_class = SuggestionSerializer

    # 내가 받은 제안 목록
    @action(detail=False, methods=["get"])
    def received(self, request):
        role = request.query_params.get("role")
        user_id = request.query_params.get("user_id")

        if role == "artist":
            queryset = self.queryset.filter(space_id__user__id=user_id)
        elif role == "space":
            queryset = self.queryset.filter(artist_id__user__id=user_id)
        else:
            return Response({"error": "role (artist/space)와 user_id 필요"}, status=400)

        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data)

    # 내가 보낸 제안 목록
    @action(detail=False, methods=["get"])
    def sent(self, request):
        role = request.query_params.get("role")
        user_id = request.query_params.get("user_id")

        if role == "artist":
            queryset = self.queryset.filter(artist_id__user__id=user_id, sender_type="artist")
        elif role == "space":
            queryset = self.queryset.filter(space_id__user__id=user_id, sender_type="space")
        else:
            return Response({"error": "role (artist/space)와 user_id 필요"}, status=400)

        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data)

    # 제안 상태 변경
    @action(detail=True, methods=["patch"])
    def status(self, request, pk=None):
        suggestion = self.get_object()
        is_accepted = request.data.get("is_accepted")

        if is_accepted is None:
            return Response({"error": "is_accepted 값 필요"}, status=400)

        suggestion.is_accepted = is_accepted
        suggestion.save()

        # 수락 시 상대방 전화번호 포함
        serializer = self.serializer_class(suggestion)
        return Response(serializer.data)

    # 아티스트 → 공간 제안
    @action(detail=False, methods=["post"], url_path="artist-to-space")
    def artist_to_space(self, request):
        data = request.data.copy()
        data["sender_type"] = "artist"
        serializer = self.serializer_class(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

    # 공간 → 아티스트 제안
    @action(detail=False, methods=["post"], url_path="space-to-artist")
    def space_to_artist(self, request):
        data = request.data.copy()
        data["sender_type"] = "space"
        serializer = self.serializer_class(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)
