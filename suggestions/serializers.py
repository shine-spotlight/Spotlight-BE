from rest_framework import serializers
from .models import Suggestion
from users.models import User

class SuggestionSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source="sender.kakao_id", read_only=True)
    receiver_name = serializers.CharField(source="receiver.kakao_id", read_only=True)

    class Meta:
        model = Suggestion
        fields = "__all__"
