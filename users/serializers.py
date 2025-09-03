from rest_framework import serializers
from .models import User

class UserSerializer(serializers.ModelSerializer):
    # phone_number를 read/write 가능하게
    class Meta:
        model = User
        fields = ['id', 'kakao_id', 'role', 'phone_number', 'created_at']
        read_only_fields = ['id', 'created_at']
