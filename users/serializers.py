from rest_framework import serializers
from .models import User

class UserSerializer(serializers.ModelSerializer):
    role = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = ['id', 'kakao_id', 'role', 'phone_number', 'created_at']
        read_only_fields = ['id', 'created_at']
    def get_isOnboarding(self, obj):
        # role, phone_number 등 필수 정보가 모두 비어있으면 True
        required_fields = [obj.role, obj.phone_number]
        return not all(required_fields)

#커밋