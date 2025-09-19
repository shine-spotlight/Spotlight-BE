from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .duckdb_adapter import get_duck_conn


def bad_request(detail: str, field: str = ""):
    payload = {"detail": detail, "code": "invalid_param"}
    if field:
        payload["field"] = field
    return Response(payload, status=400)


# ------------------ 지역/장르 정규화 ------------------
def _normalize_region_token(tok: str) -> str:
    t = tok.strip()
    if "충청북" in t or "충북" in t: return "충청북도"
    if "충청남" in t or "충남" in t: return "충청남도"
    if "전라북" in t or "전북" in t: return "전북특별자치도"
    if "전라남" in t or "전남" in t: return "전라남도"
    if "경상북" in t or "경북" in t: return "경상북도"
    if "경상남" in t or "경남" in t: return "경상남도"
    if "서울" in t: return "서울특별시"
    if "부산" in t: return "부산광역시"
    if "대구" in t: return "대구광역시"
    if "인천" in t: return "인천광역시"
    if "광주" in t: return "광주광역시"
    if "대전" in t: return "대전광역시"
    if "울산" in t: return "울산광역시"
    if "세종" in t: return "세종특별자치시"
    if "경기" in t: return "경기도"
    if "강원" in t: return "강원특별자치도"
    if "제주" in t: return "제주특별자치도"
    return t


GENRE_CHOICES = [
    "(ALL)", "대중무용", "대중음악", "무용(서양/한국무용)", "뮤지컬",
    "복합", "서양음악(클래식)", "서커스/마술", "연극", "한국음악(국악)"
]

AGE_GROUP_CHOICES = """
- -1 : 전체
- 10 : 10대
- 20 : 20대
- 30 : 30대
- 40 : 40대
- 50 : 50대
- 60 : 60대
- 70 : 70대
- 80 : 80대
"""

GENDER_CHOICES = """
- -1 : 전체
-  1 : 남성
-  2 : 여성
-  0 : 알 수 없음
"""


def _select_closest_to_mean(rows):
    valid = [r[1] for r in rows if r[1] is not None]
    if not valid:
        return []
    mean_val = sum(valid) / len(valid)
    best_row = min(
        [r for r in rows if r[1] is not None],
        key=lambda r: abs(r[1] - mean_val)
    )
    return [{
        "month": str(best_row[0])[:10],
        "forecast": best_row[1],
        "yhat_lower": best_row[2],
        "yhat_upper": best_row[3],
    }]


class DemandViewSet(viewsets.ViewSet):
    # ------------------ 내부 유틸 ------------------
    def _normalize(self, value: str):
        if not value:
            return None
        return value.strip().lower()

    def _is_all(self, value: str) -> bool:
        return str(value).strip().lower() in {"all", "(all)"}

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

    # ------------------ 1. Forecast ------------------
    @swagger_auto_schema(
        operation_summary="수요 예측 조회",
        operation_description=f"""
지역, 장르, 연령대, 성별을 기준으로 향후 수요 예측치를 반환합니다.

- region: 행정구역 (예: 서울, 부산, 경기, 전북 → 자동 정규화됨)
- genre: 장르명 (예: 뮤지컬, 연극, 대중음악 등)
- age_group: 연령대 코드  
{AGE_GROUP_CHOICES}
- gender: 성별 코드  
{GENDER_CHOICES}
- as_of: 기준월 (YYYY-MM-01)

⚠️ 조회 결과가 없을 경우, 조건을 완화하여 (ALL, ALL)까지 fallback합니다.
        """,
        manual_parameters=[
            openapi.Parameter("region", openapi.IN_QUERY, type=openapi.TYPE_STRING,
                              description="지역명 (서울/부산/경기/전북 등)", required=True),
            openapi.Parameter("genre", openapi.IN_QUERY, type=openapi.TYPE_STRING,
                              description=f"장르명 {GENRE_CHOICES}", required=True),
            openapi.Parameter("age_group", openapi.IN_QUERY, type=openapi.TYPE_STRING,
                              description=f"연령대 코드\n{AGE_GROUP_CHOICES}", required=False),
            openapi.Parameter("gender", openapi.IN_QUERY, type=openapi.TYPE_STRING,
                              description=f"성별 코드\n{GENDER_CHOICES}", required=False),
            openapi.Parameter("as_of", openapi.IN_QUERY, type=openapi.TYPE_STRING,
                              description="스냅샷 기준월 (YYYY-MM-01)", required=False),
        ],
        tags=["Demand"]
    )
    @action(detail=False, methods=["get"])
    def forecast(self, request):
        raw_region = request.query_params.get("region")
        raw_genre = request.query_params.get("genre")
        if not raw_region or not raw_genre:
            return bad_request("region과 genre는 필수입니다.", "region/genre")

        region = self._normalize(raw_region)
        genre = self._normalize(raw_genre)

        ag = self._parse_age_group2(request.query_params.get("age_group"))
        gd = self._parse_gender2(request.query_params.get("gender"))
        if ag["mode"] == "invalid":
            return bad_request("age_group 형식이 올바르지 않습니다. (-1/10/20/.../미상)", "age_group")
        if gd["mode"] == "invalid":
            return bad_request("gender 형식이 올바르지 않습니다. (-1/0/1/2/미상)", "gender")

        as_of = request.query_params.get("as_of")

        try:
            with get_duck_conn() as con:
                candidates = [
                    # region+genre+age+gender
                    ("""
                        SELECT month, forecast, yhat_lower, yhat_upper
                        FROM analytics.demand_forecast_asof
                        WHERE as_of_month = CAST(? AS DATE)
                          AND LOWER(region) = ?
                          AND LOWER(genre)  = ?
                          AND (age_group = ? OR ? IS NULL)
                          AND (gender = ? OR ? IS NULL)
                    """, [as_of, region, genre,
                          ag.get("value"), ag.get("value"),
                          gd.get("value"), gd.get("value")]),

                    # region+genre
                    ("""
                        SELECT month, forecast, yhat_lower, yhat_upper
                        FROM analytics.demand_forecast_asof
                        WHERE as_of_month = CAST(? AS DATE)
                          AND LOWER(region) = ?
                          AND LOWER(genre)  = ?
                    """, [as_of, region, genre]),

                    # ALL+genre
                    ("""
                        SELECT month, forecast, yhat_lower, yhat_upper
                        FROM analytics.demand_forecast_asof
                        WHERE as_of_month = CAST(? AS DATE)
                          AND LOWER(region) = '(all)'
                          AND LOWER(genre)  = ?
                    """, [as_of, genre]),

                    # ALL+ALL
                    ("""
                        SELECT month, forecast, yhat_lower, yhat_upper
                        FROM analytics.demand_forecast_asof
                        WHERE as_of_month = CAST(? AS DATE)
                          AND LOWER(region) = '(all)'
                          AND LOWER(genre)  = '(all)'
                    """, [as_of]),
                ]

                items = []
                for idx, (sql, params) in enumerate(candidates):
                    rows = con.execute(sql, params).fetchall()
                    forecast_vals = [r[1] for r in rows]
                    valid_forecast = [v for v in forecast_vals if v is not None]
                    print(f"\n[forecast DEBUG] candidate #{idx+1}")
                    print("SQL:", sql.strip().replace("\n", " "))
                    print("params:", params)
                    print("rows count:", len(rows))
                    print("forecast values:", forecast_vals)
                    print("valid forecast values:", valid_forecast)
                    items = _select_closest_to_mean(rows)
                    if items:
                        break

        except Exception as e:
            return bad_request(f"DuckDB 조회 중 오류: {e}", "duckdb")

        return Response({
            "region": raw_region,
            "genre": raw_genre,
            "age_group": ag.get("value"),
            "gender": self._gender_label(gd.get("value")),
            "as_of": as_of,
            "items": items or []
        })

    # ------------------ 2. Shortage ------------------
    @swagger_auto_schema(
        operation_summary="공급 부족 지수 조회",
        operation_description="공급 부족 지수(=예측 구간폭 평균)를 반환합니다.",
        tags=["Demand"]
    )
    @action(detail=False, methods=["get"])
    def shortage(self, request):
        raw_region = request.query_params.get("region")
        raw_genre = request.query_params.get("genre")
        region = self._normalize(raw_region)
        genre = self._normalize(raw_genre)
        as_of = request.query_params.get("as_of")

        if not region or not genre:
            return bad_request("region과 genre는 필수입니다.", "region/genre")

        try:
            sql = """
                SELECT AVG(yhat_upper - yhat_lower) AS shortage_index
                FROM analytics.demand_forecast_asof
                WHERE as_of_month = CAST(? AS DATE)
                  AND LOWER(region) = ?
                  AND LOWER(genre)  = ?
            """
            with get_duck_conn() as con:
                rec = con.execute(sql, [as_of, region, genre]).fetchone()
                if not rec or rec[0] is None:
                    rec = con.execute(sql, [as_of, "(all)", "(all)"]).fetchone()
            if not rec or rec[0] is None:
                return bad_request("해당 조건의 shortage_index가 없습니다.", "region/genre/as_of")
            shortage_index = rec[0]
        except Exception as e:
            return bad_request(f"DuckDB 조회 중 오류: {e}", "duckdb")

        return Response({
            "region": raw_region,
            "genre": raw_genre,
            "as_of": as_of,
            "shortage_index": shortage_index
        })

    # ------------------ 3. Recommendation ------------------
    @swagger_auto_schema(
        operation_summary="추천 지역/장르 조회",
        operation_description="특정 장르 → 인기 지역 TOP-N, 특정 지역 → 인기 장르 TOP-N 반환.",
        manual_parameters=[
            openapi.Parameter("region", openapi.IN_QUERY, type=openapi.TYPE_STRING,
                              description="지역 (서울특별시 등). (ALL) 금지", required=False),
            openapi.Parameter("genre", openapi.IN_QUERY, type=openapi.TYPE_STRING,
                              description=f"장르명 {GENRE_CHOICES}. (ALL) 금지", required=False),
            openapi.Parameter("top_n", openapi.IN_QUERY, type=openapi.TYPE_INTEGER,
                              description="상위 N개 (기본값 3)", required=False),
        ],
        tags=["Demand"]
    )
    @action(detail=False, methods=["get"])
    def recommendation(self, request):
        raw_region = request.query_params.get("region")
        raw_genre = request.query_params.get("genre")
        region = self._normalize(raw_region) if raw_region else None
        genre = self._normalize(raw_genre) if raw_genre else None

        if bool(region) == bool(genre):
            return bad_request("region 또는 genre 중 하나만 전달하세요.", "region/genre")

        try:
            top_n = max(1, int(request.query_params.get("top_n", 3)))
        except ValueError:
            top_n = 3

        try:
            with get_duck_conn() as con:
                bsql = """
                    WITH mx AS (
                        SELECT date_trunc('month', MAX(month)) AS end_month
                        FROM analytics.demand_modeling_grid
                    )
                    SELECT
                        (SELECT end_month FROM mx),
                        ((SELECT end_month FROM mx) - INTERVAL 2 MONTH),
                        ((SELECT end_month FROM mx) + INTERVAL 1 MONTH)
                """
                end_month, start_month, end_month_excl = con.execute(bsql).fetchone()

                if genre and not region:
                    sql = f"""
                        SELECT region, SUM(demand) AS total_orders
                        FROM analytics.demand_modeling_grid
                        WHERE month >= ? AND month < ?
                          AND LOWER(genre) = ?
                          AND age_group = -1 AND gender = -1
                          AND region IS NOT NULL
                          AND region NOT IN ('(ALL)', 'all')
                        GROUP BY region
                        ORDER BY total_orders DESC NULLS LAST
                        LIMIT {top_n}
                    """
                    rows = con.execute(sql, [start_month, end_month_excl, genre]).fetchall()
                    results = [{"region": r[0], "total_orders": int(r[1])} for r in rows]
                    return Response({
                        "pivot": "by_genre",
                        "genre": raw_genre,
                        "period": {"start_month": str(start_month)[:10],
                                   "end_month": str(end_month)[:10]},
                        "top_n": top_n,
                        "results": results
                    })

                if region and not genre:
                    sql = f"""
                        SELECT genre, SUM(demand) AS total_orders
                        FROM analytics.demand_modeling_grid
                        WHERE month >= ? AND month < ?
                          AND LOWER(region) = ?
                          AND age_group = -1 AND gender = -1
                          AND genre IS NOT NULL
                          AND genre NOT IN ('(ALL)', 'all')
                        GROUP BY genre
                        ORDER BY total_orders DESC NULLS LAST
                        LIMIT {top_n}
                    """
                    rows = con.execute(sql, [start_month, end_month_excl, region]).fetchall()
                    results = [{"genre": r[0], "total_orders": int(r[1])} for r in rows]
                    return Response({
                        "pivot": "by_region",
                        "region": raw_region,
                        "period": {"start_month": str(start_month)[:10],
                                   "end_month": str(end_month)[:10]},
                        "top_n": top_n,
                        "results": results
                    })
        except Exception as e:
            return bad_request(f"DuckDB 조회 중 오류: {e}", "duckdb")
