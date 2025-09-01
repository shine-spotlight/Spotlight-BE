from rest_framework import serializers
from .models import Artist
from categories.models import Category


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']  # 필요한 필드만 노출


class ArtistSerializer(serializers.ModelSerializer):
    # 응답용 (category 객체 전체 반환)
    category = CategorySerializer(read_only=True)

    # 요청용 (category id로 전달받아 매핑)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source='category',
        write_only=True,
        required=False,
        allow_null=True
    )

    class Meta:
        model = Artist
        fields = '__all__'
