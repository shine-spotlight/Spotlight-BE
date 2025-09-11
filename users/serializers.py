from rest_framework import serializers
from .models import User

class UserSerializer(serializers.ModelSerializer):
    role = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = ['id', 'kakao_id', 'role', 'phone_number', 'created_at']
        read_only_fields = ['id', 'created_at']

#커밋