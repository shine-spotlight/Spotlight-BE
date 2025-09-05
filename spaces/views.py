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
        serializer = SpaceSerializer(space, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # 2. 기본정보 입력
    @action(detail=True, methods=["post"])
    def base(self, request, pk=None):
        space = self.get_object()
        serializer = SpaceSerializer(space, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # 3. 상세정보 입력
    @action(detail=True, methods=["post"], url_path="detail")
    def detail_info(self, request, pk=None):
        space = self.get_object()
        serializer = SpaceSerializer(space, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # 4. 수용 인원 입력
    @action(detail=True, methods=["post"])
    def capacity(self, request, pk=None):
        space = self.get_object()
        serializer = SpaceSerializer(space, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # 5. 선호 공연 카테고리 입력
    @action(detail=True, methods=["post"])
    def preference(self, request, pk=None):
        space = self.get_object()
        serializer = SpaceSerializer(space, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # 필터링
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
