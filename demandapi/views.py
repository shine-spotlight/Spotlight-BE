from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .duckdb_adapter import get_forecast, get_duck_conn

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
    
    def _parse_age_group(self, value: str):
        if value is None or str(value).strip() == "":
            return None
        v = str(value).strip()
        return (f"{v}대") if v.isdigit() else v.lower()
    
    def _parse_gender(self, value: str):
        if value is None or str(value).strip() == "":
            return None
        v = str(value).strip().lower()

        # 숫자 직접 맵핑
        if v.isdigit():
            n = int(v)
            return n if n in (0, 1, 2) else None

        # 문자 맵핑
        if v in {"남", "남성", "m", "male"}:
            return 1
        if v in {"여", "여성", "f", "female"}:
            return 2
        if v in {"알수없음", "알 수 없음", "unknown", "u", "x", "미상", "기타"}:
            return 0

        return None

    def _gender_label(self, g: int | None) -> str | None:
        if g is None:
            return None
        return {1: "남성", 2: "여성", 0: "알 수 없음"}.get(g, None)
    
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
                    "genre": "대중가요",
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
        gender_q = self._parse_gender(request.query_params.get("gender"))
        as_of = request.query_params.get("as_of") or "2025-09-01"
        
        if not region or not genre:
            return bad_request("region과 genre는 필수입니다.", "region/genre")
        
        try:
            rows = get_forecast(
                region=region, genre=genre,
                age_group=age_group, gender=gender_q,
                as_of=as_of
            )
        except Exception as e:
            return bad_request(f"DuckDB 조회 중 오류: {e}", "duckdb")
        
        items = [
            {
                "month": str(r["month"])[:10],
                "forecast": r["forecast"],
                "yhat_lower": r.get("yhat_lower"),
                "yhat_upper": r.get("yhat_upper"),
            }
            for r in rows
        ]

        # TODO: DuckDB 쿼리
        return Response({
            "region": region,
            "genre": genre,
            "age_group": age_group,
            "gender": self._gender_label(gender_q),
            "as_of": as_of,
            "items": items
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
                    "region": "서울특별시",
                    "genre": "",
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
        as_of = request.query_params.get("as_of") or "2025-09-01"

        if not region or not genre:
            return bad_request("region과 genre는 필수입니다.", "region/genre")
        try:
            sql = """
                SELECT shortage_index
                FROM analytics.shortage_index_asof
                WHERE as_of_month = DATE ?
                  AND region = ?
                  AND genre  = ?
                LIMIT 1
            """
            with get_duck_conn() as con:
                rec = con.execute(sql, [as_of, region, genre]).fetchone()
            if not rec:
                return bad_request("해당 조건의 shortage_index가 없습니다.", "region/genre/as_of")
            shortage_index = rec[0]
        except Exception as e:
            return bad_request(f"DuckDB 조회 중 오류: {e}", "duckdb")

        # TODO: DuckDB 쿼리
        return Response({"region": region, "genre": genre, "as_of": as_of, "shortage_index": shortage_index})
        
        #return Response({"region": region, "genre": genre, "shortage_index": 0.73})

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
                    "recommendations": ["서울특별시 마포구", "경기도 성남시"]
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
        return Response({"recommendations": ["서울특별시 마포구", "경기도 성남시"]})
