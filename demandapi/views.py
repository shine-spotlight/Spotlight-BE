from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

class DemandViewSet(viewsets.ViewSet):
    @action(detail=False, methods=["get"])
    def forecast(self, request):
        region = request.query_params.get("region")
        genre = request.query_params.get("genre")
        age_group = request.query_params.get("age_group")
        gender = request.query_params.get("gender")
        # TODO: DuckDB 쿼리
        return Response({"region": region, "genre": genre, "forecast": [10, 15, 20]})

    @action(detail=False, methods=["get"])
    def shortage(self, request):
        # TODO: DuckDB 쿼리
        return Response({"shortage_index": 0.73})

    @action(detail=False, methods=["get"])
    def recommendation(self, request):
        # TODO: DuckDB 쿼리
        return Response({"recommendations": ["서울 마포구", "경기 성남시"]})
