from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Space
from .serializers import SpaceSerializer

class SpaceViewSet(viewsets.ModelViewSet):
    queryset = Space.objects.all()
    serializer_class = SpaceSerializer

    # 1. 사업자등록번호 입력
    @action(detail=True, methods=["post"])
    def business(self, request, pk=None):
        space = self.get_object()
        reg_no = request.data.get("business_registration_number")
        if not reg_no:
            return Response({"error": "사업자 등록번호가 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)
        space.business_registration_number = reg_no
        space.save()
        return Response(SpaceSerializer(space).data)

    # 2. 기본정보 입력
    @action(detail=True, methods=["post"])
    def base(self, request, pk=None):
        space = self.get_object()
        for field in ["place_name", "address", "kakao_map_link"]:
            if field in request.data:
                setattr(space, field, request.data[field])
        space.save()
        return Response(SpaceSerializer(space).data)

    # 3. 상세정보 입력
    @action(detail=True, methods=["post"])
    def detail(self, request, pk=None):
        space = self.get_object()
        for field in ["description", "category", "atmosphere", "place_image_url"]:
            if field in request.data:
                setattr(space, field, request.data[field])
        space.save()
        return Response(SpaceSerializer(space).data)

    # 4. 수용 인원 입력
    @action(detail=True, methods=["post"])
    def capacity(self, request, pk=None):
        space = self.get_object()
        for field in ["capacity_seated", "capacity_standing"]:
            if field in request.data:
                setattr(space, field, request.data[field])
        space.save()
        return Response(SpaceSerializer(space).data)

    # 5. 선호 공연 카테고리 입력
    @action(detail=True, methods=["post"])
    def preference(self, request, pk=None):
        space = self.get_object()
        categories = request.data.get("preferred_categories")
        if categories:
            space.preferred_categories.set(categories)
        space.save()
        return Response(SpaceSerializer(space).data)

    # 필터링: GET /api/v1/spaces/filter/
    @action(detail=False, methods=["get"])
    def filter(self, request):
        queryset = self.queryset
        region = request.query_params.get("region")
        category = request.query_params.get("category")
        cap_min = request.query_params.get("cap_min")
        cap_max = request.query_params.get("cap_max")

        if region:
            queryset = queryset.filter(place_region__icontains=region)
        if category:
            queryset = queryset.filter(category=category)
        if cap_min:
            queryset = queryset.filter(capacity_seated__gte=cap_min)
        if cap_max:
            queryset = queryset.filter(capacity_seated__lte=cap_max)

        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
