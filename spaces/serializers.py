from rest_framework import serializers
from .models import Space
from users.models import User


class SpaceSerializer(serializers.ModelSerializer):
    # ✅ User.phone_number 가져오기
    phone_number = serializers.CharField(source="user.phone_number", read_only=True)

    class Meta:
        model = Space
        fields = "__all__"
