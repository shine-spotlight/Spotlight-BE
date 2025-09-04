from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Suggestion
from .serializers import SuggestionSerializer
from notifications.models import Notification  # ✅ 알림 추가


class SuggestionViewSet(viewsets.ModelViewSet):
    queryset = Suggestion.objects.all()
    serializer_class = SuggestionSerializer

    # ✅ 제안 생성 시 알림 (제안 받은 사람에게)
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        suggestion = serializer.save()

        # 알림 전송
        if suggestion.sender_type == "artist":
            # 아티스트 → 공간
            Notification.objects.create(
                user=suggestion.space.user,
                content=f"{suggestion.artist.name}이(가) 제안을 보냈습니다.",
                target_link=f"http://127.0.0.1:8000/api/v1/suggestions/{suggestion.id}/"
            )
        else:
            # 공간 → 아티스트
            Notification.objects.create(
                user=suggestion.artist.user,
                content=f"{suggestion.space.place_name}이(가) 제안을 보냈습니다.",
                target_link=f"http://127.0.0.1:8000/api/v1/suggestions/{suggestion.id}/"
            )

        return Response(self.get_serializer(suggestion).data, status=status.HTTP_201_CREATED)

    # ✅ 제안 수락 시 알림 (보낸 사람에게)
    @action(detail=True, methods=["patch"])
    def accept(self, request, pk=None):
        suggestion = self.get_object()
        suggestion.is_accepted = True
        suggestion.save()

        # 알림 전송
        if suggestion.sender_type == "artist":
            # 아티스트가 보냈다면 → 아티스트에게 수락 알림
            Notification.objects.create(
                user=suggestion.artist.user,
                content=f"{suggestion.space.place_name}이(가) 당신의 제안을 수락했습니다.",
                target_link=f"http://127.0.0.1:8000/api/v1/suggestions/{suggestion.id}/"
            )
        else:
            # 공간이 보냈다면 → 공간 보유자에게 수락 알림
            Notification.objects.create(
                user=suggestion.space.user,
                content=f"{suggestion.artist.name}이(가) 당신의 제안을 수락했습니다.",
                target_link=f"http://127.0.0.1:8000/api/v1/suggestions/{suggestion.id}/"
            )

        return Response(SuggestionSerializer(suggestion).data, status=status.HTTP_200_OK)
