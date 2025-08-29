from rest_framework import serializers
from .models import ArtistEquipment

class ArtistEquipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArtistEquipment
        fields = '__all__'
