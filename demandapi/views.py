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

    def _is_all(self, value: str) -> bool:
        return str(value).strip().lower() in {"all", "(all)"}

    # age_group: -1=전체, 미상=IS NULL, 숫자(10/20/..)=그 값
    def _parse_age_group2(self, value: str | None):
        if value is None or str(value).strip() == "":
            return {"mode": "unspecified", "value": None}
        v = str(value).strip().lower()
        if v == "-1":
            return {"mode": "value", "value": -1}
        if v in {"미상", "알수없음", "알 수 없음", "unknown", "null"}:
            return {"mode": "unknown", "value": None}
        if v.isdigit():
            return {"mode": "value", "value": int(v)}
        import re
        m = re.match(r"^(\d+)", v)
        if m:
            return {"mode": "value", "value": int(m.group(1))}
        return {"mode": "invalid", "value": None}
    
    def _parse_gender2(self, value: str | None):
        if value is None or str(value).strip() == "":
            return {"mode": "unspecified", "value": None}
        v = str(value).strip().lower()
        if v == "-1":
            return {"mode": "value", "value": -1}
        if v in {"0", "미상", "알수없음", "알 수 없음", "unknown", "u", "x"}:
            return {"mode": "value", "value": 0}
        if v in {"1", "남", "남성", "m", "male"}:
            return {"mode": "value", "value": 1}
        if v in {"2", "여", "여성", "f", "female"}:
            return {"mode": "value", "value": 2}
        return {"mode": "invalid", "value": None}

    def _gender_label(self, g: int | None) -> str | None:
        if g is None:
            return None
        return {1: "남성", 2: "여성", 0: "알 수 없음", -1: "전체"}.get(g, None)
    
    @swagger_auto_schema(
        operation_summary="수요 예측 조회",
        operation_description="지역, 장르, 연령대, 성별을 기준으로 수요 예측 데이터를 반환합니다.",
        manual_parameters=[
            openapi.Parameter('region', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='지역', required=True),
            openapi.Parameter('genre',  openapi.IN_QUERY, type=openapi.TYPE_STRING, description='장르', required=True),
            openapi.Parameter('age_group', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='연령대', required=False),
            openapi.Parameter('gender',    openapi.IN_QUERY, type=openapi.TYPE_STRING, description='성별', required=False),
            openapi.Parameter('as_of',     openapi.IN_QUERY, type=openapi.TYPE_STRING, description='스냅샷 기준월(YYYY-MM-01)', required=False),
        ],
        responses={200: openapi.Response(
        description="수요 예측 결과",
        examples={
            "application/json": {
                "region": "서울특별시",
                "genre": "뮤지컬",
                "age_group": "20",   # "전체" | "미상" | "10/20/.."
                "gender": "남성",    # "전체" | "알 수 없음" | "남성" | "여성"
                "as_of": "2025-09-01",
                "items": [
                    {"month":"2025-10-01","forecast":1234.0,"yhat_lower":1100.0,"yhat_upper":1360.0},
                    {"month":"2025-11-01","forecast":1180.0,"yhat_lower":1050.0,"yhat_upper":1310.0},
                    {"month":"2025-12-01","forecast":1400.0,"yhat_lower":1260.0,"yhat_upper":1540.0}
                ]
            }
            }
        )},
        tags=["Demand"]
    )
    @action(detail=False, methods=["get"])
    def forecast(self, request):
        raw_region = request.query_params.get("region")
        raw_genre  = request.query_params.get("genre")
        if not raw_region or not raw_genre:
            return bad_request("region과 genre는 필수입니다.", "region/genre")

        region = self._normalize(raw_region)
        genre  = self._normalize(raw_genre)

        ag = self._parse_age_group2(request.query_params.get("age_group"))
        gd = self._parse_gender2(request.query_params.get("gender"))
        if ag["mode"] == "invalid":
            return bad_request("age_group 형식이 올바르지 않습니다. (-1/10/20/.../미상)", "age_group")
        if gd["mode"] == "invalid":
            return bad_request("gender 형식이 올바르지 않습니다. (-1/0/1/2/미상)", "gender")

        as_of = request.query_params.get("as_of")  # None이면 어댑터가 최신으로 처리

        # 어댑터 규약: None → IS NULL, -1/0/1/2 → '='
        try:
            # forecast 쿼리에서 as_of_month = CAST(? AS DATE)로 변경
            sql = """
                SELECT month, forecast, yhat_lower, yhat_upper
                FROM analytics.demand_forecast_asof
                WHERE as_of_month = CAST(? AS DATE)
                  AND LOWER(region) = ?
                  AND LOWER(genre)  = ?
            """
            with get_duck_conn() as con:
                rows = con.execute(
                    sql,
                    [as_of, region, genre]
                ).fetchall()
        except Exception as e:
            return bad_request(f"DuckDB 조회 중 오류: {e}", "duckdb")

        items = [{
            "month": str(r[0])[:10],
            "forecast": r[1],
            "yhat_lower": r[2],
            "yhat_upper": r[3],
        } for r in (rows or [])]

        if not items:
            return bad_request("해당 조합의 예측 결과가 없습니다. 필터(-1/미상/(ALL))를 확인하세요.", "filters")

        return Response({
            "region": raw_region,
            "genre": raw_genre,
            "age_group": (
                "전체" if (ag["mode"]=="value" and ag["value"]==-1)
                else ("미상" if ag["mode"]=="unknown" else (ag["value"] if ag["mode"]=="value" else None))
            ),
            "gender": (
                "전체" if (gd["mode"]=="value" and gd["value"]==-1)
                else ("알 수 없음" if (gd["mode"]=="value" and gd["value"]==0) else (self._gender_label(gd["value"]) if gd["mode"]=="value" else None))
            ),
            "as_of": as_of,
            "items": items
        })


    @swagger_auto_schema(
        operation_summary="공급 부족 지수 조회",
        operation_description="지역, 장르별 공급 부족 지수를 반환합니다.",
        manual_parameters=[
            openapi.Parameter('region', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='지역', required=True),
            openapi.Parameter('genre',  openapi.IN_QUERY, type=openapi.TYPE_STRING, description='장르', required=True),
            openapi.Parameter('as_of',  openapi.IN_QUERY, type=openapi.TYPE_STRING, description='기준월(YYYY-MM-01)', required=False),
        ],
        responses={200: openapi.Response(
            description="공급 부족 지수 결과",
            examples={
                "application/json": {
                    "region": "서울특별시",
                    "genre": "뮤지컬",
                    "as_of": "2025-09-01",
                    "shortage_index": 0.73
                }
            }
        )},
        tags=["Demand"]
    )
    @action(detail=False, methods=["get"])
    def shortage(self, request):
        raw_region = request.query_params.get("region")
        raw_genre  = request.query_params.get("genre")
        region = self._normalize(raw_region)
        genre  = self._normalize(raw_genre)
        as_of  = request.query_params.get("as_of") or "2025-09-01"

        if not region or not genre:
            return bad_request("region과 genre는 필수입니다.", "region/genre")
        try:
            # shortage 쿼리에서 as_of_month = CAST(? AS DATE)로 변경
            sql = """
                SELECT shortage_index
                FROM analytics.shortage_index_asof
                WHERE as_of_month = CAST(? AS DATE)
                  AND LOWER(region) = ?
                  AND LOWER(genre)  = ?
                LIMIT 1
            """
            with get_duck_conn() as con:
                rec = con.execute(sql, [as_of, region, genre]).fetchone()
            if not rec:
                return bad_request("해당 조건의 shortage_index가 없습니다.", "region/genre/as_of")
            shortage_index = rec[0]
        except Exception as e:
            return bad_request(f"DuckDB 조회 중 오류: {e}", "duckdb")

        return Response({"region": raw_region, "genre": raw_genre, "as_of": as_of, "shortage_index": shortage_index})
  
        #return Response({"region": region, "genre": genre, "shortage_index": 0.73})

    @swagger_auto_schema(
        operation_summary="추천 지역/장르 조회",
        operation_description="입력된 지역 또는 장르를 기반으로 추천 지역/장르를 반환합니다.",
        manual_parameters=[
            openapi.Parameter('region', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='지역(특정값). (ALL)은 불가', required=False),
            openapi.Parameter('genre',  openapi.IN_QUERY, type=openapi.TYPE_STRING, description='장르(특정값). (ALL)은 불가', required=False),
            openapi.Parameter('top_n',  openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description='상위 N (기본 3)', required=False),
        ],
        responses={200: openapi.Response(
            description="추천 결과",
            examples={
                # 장르 pivot 예시
                "application/json (by_genre)": {
                    "pivot": "by_genre",
                    "genre": "뮤지컬",
                    "period": {"start_month": "2025-07-01", "end_month": "2025-09-01"},
                    "top_n": 3,
                    "results": [
                        {"region": "서울특별시 마포구", "total_orders": 15000},
                        {"region": "경기도 성남시", "total_orders": 12000},
                        {"region": "부산광역시 해운대구", "total_orders": 11000}
                    ]
                },
                # 지역 pivot 예시
                "application/json (by_region)": {
                    "pivot": "by_region",
                    "region": "서울특별시",
                    "period": {"start_month": "2025-07-01", "end_month": "2025-09-01"},
                    "top_n": 3,
                    "results": [
                        {"genre": "뮤지컬", "total_orders": 12890},
                        {"genre": "연극",   "total_orders": 10930},
                        {"genre": "대중음악", "total_orders": 10110}
                    ]
                }
            }
    )},
        tags=["Demand"]
    )
    @action(detail=False, methods=["get"])
    def recommendation(self, request):
        raw_region = request.query_params.get("region")
        raw_genre  = request.query_params.get("genre")
        region = self._normalize(raw_region) if raw_region else None
        genre  = self._normalize(raw_genre)  if raw_genre  else None

        # 하나만 전달 & (ALL) 금지
        if bool(region) == bool(genre):
            return bad_request("region 또는 genre 중 하나만 전달하세요.", "region/genre")
        if (raw_region and self._is_all(raw_region)) or (raw_genre and self._is_all(raw_genre)):
            return bad_request("추천 조회에서는 (ALL)을 사용할 수 없습니다. 구체 값을 전달하세요.", "region/genre")

        # top_n
        try:
            top_n = max(1, int(request.query_params.get("top_n", 3)))
        except ValueError:
            top_n = 3

        try:
            with get_duck_conn() as con:
                # 최신 월 기준 최근 3개월 경계
                bsql = """
                    WITH mx AS (
                        SELECT date_trunc('month', MAX(month)) AS end_month
                        FROM analytics.demand_modeling_grid
                    )
                    SELECT
                        (SELECT end_month FROM mx)                                  AS end_month,
                        ((SELECT end_month FROM mx) - INTERVAL 2 MONTH)             AS start_month,
                        ((SELECT end_month FROM mx) + INTERVAL 1 MONTH)             AS end_month_excl
                """
                end_month, start_month, end_month_excl = con.execute(bsql).fetchone()
                if not end_month:
                    return bad_request("analytics.demand_modeling_grid에 데이터가 없습니다.", "duckdb")

                if genre and not region:
                    # 장르 → 최근3개월 지역 TOP N (전체 레벨에서 집계: age_group=-1, gender=-1)
                    sql = f"""
                        SELECT region, SUM(demand) AS total_orders
                        FROM analytics.demand_modeling_grid
                        WHERE month >= ? AND month < ?
                          AND LOWER(genre) = ?
                          AND age_group = -1
                          AND gender    = -1
                          AND region IS NOT NULL
                        GROUP BY region
                        ORDER BY total_orders DESC NULLS LAST
                        LIMIT {top_n}
                    """
                    rows = con.execute(sql, [start_month, end_month_excl, genre]).fetchall()
                    results = [{"region": r[0], "total_orders": int(r[1]) if r[1] is not None else 0} for r in rows]
                    return Response({
                        "pivot": "by_genre",
                        "genre": raw_genre,  # 응답에 장르명 포함
                        "period": {"start_month": str(start_month)[:10], "end_month": str(end_month)[:10]},
                        "top_n": top_n,
                        "results": results
                    })

                if region and not genre:
                    # 지역 → 최근3개월 장르 TOP N (전체 레벨에서 집계)
                    sql = f"""
                        SELECT genre, SUM(demand) AS total_orders
                        FROM analytics.demand_modeling_grid
                        WHERE month >= ? AND month < ?
                          AND LOWER(region) = ?
                          AND age_group = -1
                          AND gender    = -1
                          AND genre IS NOT NULL
                        GROUP BY genre
                        ORDER BY total_orders DESC NULLS LAST
                        LIMIT {top_n}
                    """
                    rows = con.execute(sql, [start_month, end_month_excl, region]).fetchall()
                    results = [{"genre": r[0], "total_orders": int(r[1]) if r[1] is not None else 0} for r in rows]
                    return Response({
                        "pivot": "by_region",
                        "region": raw_region,  
                        "period": {"start_month": str(start_month)[:10], "end_month": str(end_month)[:10]},
                        "top_n": top_n,
                        "results": results
                    })

        except Exception as e:
            return bad_request(f"DuckDB 조회 중 오류: {e}", "duckdb")