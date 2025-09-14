from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
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

    @swagger_auto_schema(
        operation_summary="수요 예측 조회",
        operation_description="지역, 장르, 연령대, 성별을 기준으로 수요 예측 데이터를 반환합니다.",
        manual_parameters=[
            openapi.Parameter('region', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='지역', required=True),
            openapi.Parameter('genre', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='장르', required=True),
            openapi.Parameter('age_group', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='연령대', required=False),
            openapi.Parameter('gender', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='성별', required=False),
        ],
        responses={200: openapi.Response(
            description="수요 예측 결과",
            examples={
                "application/json": {
                    "region": "서울",
                    "genre": "락",
                    "age_group": "20대",
                    "gender": "남성",
                    "forecast": [10, 15, 20]
                }
            }
        )},
        tags=["Demand"]
    )
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

    @swagger_auto_schema(
        operation_summary="공급 부족 지수 조회",
        operation_description="지역, 장르별 공급 부족 지수를 반환합니다.",
        manual_parameters=[
            openapi.Parameter('region', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='지역', required=True),
            openapi.Parameter('genre', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='장르', required=True),
        ],
        responses={200: openapi.Response(
            description="공급 부족 지수 결과",
            examples={
                "application/json": {
                    "region": "서울",
                    "genre": "락",
                    "shortage_index": 0.73
                }
            }
        )},
        tags=["Demand"]
    )
    @action(detail=False, methods=["get"])
    def shortage(self, request):
        region = self._normalize(request.query_params.get("region"))
        genre = self._normalize(request.query_params.get("genre"))
        if not region or not genre:
            return bad_request("region과 genre는 필수입니다.", "region/genre")
        # TODO: DuckDB 쿼리
        return Response({"region": region, "genre": genre, "shortage_index": 0.73})

    @swagger_auto_schema(
        operation_summary="추천 지역/장르 조회",
        operation_description="입력된 지역 또는 장르를 기반으로 추천 지역/장르를 반환합니다.",
        manual_parameters=[
            openapi.Parameter('region', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='지역', required=False),
            openapi.Parameter('genre', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='장르', required=False),
        ],
        responses={200: openapi.Response(
            description="추천 결과",
            examples={
                "application/json": {
                    "recommendations": ["서울 마포구", "경기 성남시"]
                }
            }
        )},
        tags=["Demand"]
    )
    @action(detail=False, methods=["get"])
    def recommendation(self, request):
        region = self._normalize(request.query_params.get("region"))
        genre = self._normalize(request.query_params.get("genre"))
        if not region and not genre:
            return bad_request("region 또는 genre 중 하나는 필수입니다.", "region/genre")
        # TODO: DuckDB 쿼리
        return Response({"recommendations": ["서울 마포구", "경기 성남시"]})
