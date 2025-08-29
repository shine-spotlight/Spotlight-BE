from rest_framework import serializers
from .models import Artist

class ArtistSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField(source='user.phone_number', read_only=True)
    category_name = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Artist
        fields = '__all__'

    def create(self, validated_data):
        category_name = validated_data.pop("category_name", None)

        # category_name이 있으면 Category 테이블에 추가/연결
        if category_name:
            category, created = Category.objects.get_or_create(name=category_name)
            validated_data["category"] = category

        return super().create(validated_data)
    
