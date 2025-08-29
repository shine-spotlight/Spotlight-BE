from rest_framework import serializers
from .models import SpaceAvailableDate

class SpaceAvailableDateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpaceAvailableDate
        fields = '__all__'
