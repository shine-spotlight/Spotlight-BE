from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

def bad_request(detail: str, field: str = ""):
    payload = {"detail": detail, "code": "invalid_param"}
    if field:
        payload["field"] = field
    return Response(payload, status=400)

class DemandViewSet(viewsets.ViewSet):
    def _normalize(self, value: str):
        if not value:
            return None
        return value.strip().lower()

    @action(detail=False, methods=["get"])
    def forecast(self, request):
        region = self._normalize(request.query_params.get("region"))
        genre = self._normalize(request.query_params.get("genre"))
        age_group = self._normalize(request.query_params.get("age_group"))
        gender = self._normalize(request.query_params.get("gender"))
        if not region or not genre:
            return bad_request("region과 genre는 필수입니다.", "region/genre")
        # TODO: DuckDB 쿼리
        return Response({
            "region": region,
            "genre": genre,
            "age_group": age_group,
            "gender": gender,
            "forecast": [10, 15, 20]
        })

    @action(detail=False, methods=["get"])
    def shortage(self, request):
        region = self._normalize(request.query_params.get("region"))
        genre = self._normalize(request.query_params.get("genre"))
        if not region or not genre:
            return bad_request("region과 genre는 필수입니다.", "region/genre")
        # TODO: DuckDB 쿼리
        return Response({"region": region, "genre": genre, "shortage_index": 0.73})

    @action(detail=False, methods=["get"])
    def recommendation(self, request):
        region = self._normalize(request.query_params.get("region"))
        genre = self._normalize(request.query_params.get("genre"))
        if not region and not genre:
            return bad_request("region 또는 genre 중 하나는 필수입니다.", "region/genre")
        # TODO: DuckDB 쿼리
        return Response({"recommendations": ["서울 마포구", "경기 성남시"]})
