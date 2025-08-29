from rest_framework import serializers
from .models import Artist
from categories.models import Category

class ArtistSerializer(serializers.ModelSerializer):
    # 기존 카테고리 선택
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source='category',
        required=False,
        allow_null=True
    )

    # 새 카테고리 직접 입력
    new_category = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Artist
        fields = '__all__'

    def create(self, validated_data):
        # ✅ new_category 값이 있으면 새 카테고리 생성
        new_category_name = validated_data.pop('new_category', None)

        if new_category_name:
            category, _ = Category.objects.get_or_create(name=new_category_name)
            validated_data['category'] = category

        return super().create(validated_data)

    def update(self, instance, validated_data):
        # ✅ 업데이트에서도 new_category 동작
        new_category_name = validated_data.pop('new_category', None)

        if new_category_name:
            category, _ = Category.objects.get_or_create(name=new_category_name)
            validated_data['category'] = category

        return super().update(instance, validated_data)

