from rest_framework import serializers
from .models import SpaceEquipment

class SpaceEquipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpaceEquipment
        fields = '__all__'
