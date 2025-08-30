from rest_framework import serializers
from .models import Artist
from categories.models import Category

class ArtistSerializer(serializers.ModelSerializer):
    # 기존 카테고리 선택 (FK)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source='category',
        required=False,
        allow_null=True
    )

    class Meta:
        model = Artist
        fields = '__all__'
