from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Artist
from .serializers import ArtistSerializer

class ArtistViewSet(viewsets.ModelViewSet):
    queryset = Artist.objects.all()
    serializer_class = ArtistSerializer

    # 1. 기본정보 입력
    @action(detail=True, methods=["post"])
    def basic(self, request, pk=None):
        artist = self.get_object()
        data = {
            "name": request.data.get("name"),
            "bio": request.data.get("bio"),
            "number_of_members": request.data.get("number_of_members"),
            "category": request.data.get("category"),
            "custom_category": request.data.get("custom_category"),
        }
        for field, value in data.items():
            if value is not None:
                setattr(artist, field, value)
        artist.save()
        return Response(ArtistSerializer(artist).data, status=status.HTTP_200_OK)

    # 2. 활동지역 입력
    @action(detail=True, methods=["post"])
    def region(self, request, pk=None):
        artist = self.get_object()
        region = request.data.get("region")
        if not region:
            return Response({"error": "region is required"}, status=status.HTTP_400_BAD_REQUEST)
        artist.region = [region] if isinstance(region, str) else region
        artist.save()
        return Response(ArtistSerializer(artist).data)

    # 3. 프로필 + 포트폴리오
    @action(detail=True, methods=["post"])
    def profile(self, request, pk=None):
        artist = self.get_object()
        if "profile_image_url" in request.data:
            artist.profile_image_url = request.data["profile_image_url"]
        if "portfolio_links" in request.data:
            links = request.data["portfolio_links"]
            if isinstance(links, str):
                artist.portfolio_links = [links]
            else:
                artist.portfolio_links = links
        artist.save()
        return Response(ArtistSerializer(artist).data)

    # 4. 희망페이, 무료공연 여부
    @action(detail=True, methods=["post"])
    def condition(self, request, pk=None):
        artist = self.get_object()
        if "desired_pay" in request.data:
            artist.desired_pay = request.data["desired_pay"]
        if "is_free_allowed" in request.data:
            artist.is_free_allowed = request.data["is_free_allowed"]
        artist.save()
        return Response(ArtistSerializer(artist).data)

    # 필터링
    @action(detail=False, methods=["get"])
    def filter(self, request):
        queryset = self.queryset
        region = request.query_params.get("region")
        category = request.query_params.get("category")
        pay_min = request.query_params.get("pay_min")
        pay_max = request.query_params.get("pay_max")

        if region:
            queryset = queryset.filter(region__icontains=region)
        if category:
            queryset = queryset.filter(category__name__icontains=category)
        if pay_min:
            queryset = queryset.filter(desired_pay__gte=pay_min)
        if pay_max:
            queryset = queryset.filter(desired_pay__lte=pay_max)

        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
