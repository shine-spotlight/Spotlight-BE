from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
<<<<<<< HEAD
from .duckdb_adapter import get_forecast, get_duck_conn
=======
from .duckdb_adapter import get_duck_conn
>>>>>>> c9f3e1d6b67b82bbf25fdbcdb82ff91a384c848f

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
    # 널 제외한 forecast만 모으기
    valid = [r[1] for r in rows if r[1] is not None]
    if not valid:
        return []
    mean_val = sum(valid) / len(valid)
    # 평균과 forecast 차이가 가장 작은 row 고르기
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

<<<<<<< HEAD
=======
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

>>>>>>> c9f3e1d6b67b82bbf25fdbcdb82ff91a384c848f
    def _gender_label(self, g: int | None) -> str | None:
        if g is None:
            return None
        return {1: "남성", 2: "여성", 0: "알 수 없음", -1: "전체"}.get(g, None)
<<<<<<< HEAD
    
=======

    # ------------------ 1. Forecast ------------------
>>>>>>> c9f3e1d6b67b82bbf25fdbcdb82ff91a384c848f
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

⚠️ 조회 결과가 없을 경우, `(ALL, genre)` → `(ALL, ALL)` 순으로 fallback합니다.
        """,
        manual_parameters=[
<<<<<<< HEAD
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
=======
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
>>>>>>> c9f3e1d6b67b82bbf25fdbcdb82ff91a384c848f
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

<<<<<<< HEAD
        as_of = request.query_params.get("as_of")  # None이면 어댑터가 최신으로 처리

        # 어댑터 규약: None → IS NULL, -1/0/1/2 → '='
        try:
            rows = get_forecast(
                region=region,
                genre=genre,
                as_of=as_of,
                age_group=(
                    -1 if ag["mode"]=="value" and ag["value"]==-1
                    else (None if ag["mode"]=="unknown" else (ag["value"] if ag["mode"]=="value" else None))
                ),
                gender=(
                    -1 if gd["mode"]=="value" and gd["value"]==-1
                    else (0 if gd["mode"]=="value" and gd["value"]==0 else (gd["value"] if gd["mode"]=="value" else None))
                )
            )
        except Exception as e:
            return bad_request(f"DuckDB 조회 중 오류: {e}", "duckdb")

        items = [{
            "month": str(r.get("month"))[:10],
            "forecast": r.get("forecast"),
            "yhat_lower": r.get("yhat_lower"),
            "yhat_upper": r.get("yhat_upper"),
        } for r in (rows or [])]

        if not items:
            return bad_request("해당 조합의 예측 결과가 없습니다. 필터(-1/미상/(ALL))를 확인하세요.", "filters")
=======
        as_of = request.query_params.get("as_of")

        try:
            with get_duck_conn() as con:
                # 1차 시도: region + genre
                sql = """
                    SELECT month, forecast, yhat_lower, yhat_upper
                    FROM analytics.demand_forecast_asof
                    WHERE as_of_month = CAST(? AS DATE)
                      AND LOWER(region) = ?
                      AND LOWER(genre)  = ?
                """
                rows = con.execute(sql, [as_of, region, genre]).fetchall()
                items = _select_closest_to_mean(rows)

                # ✅ 전부 None이거나 없으면 fallback
                if not items:
                    fallback_sql = """
                        SELECT month, forecast, yhat_lower, yhat_upper
                        FROM analytics.demand_forecast_asof
                        WHERE as_of_month = CAST(? AS DATE)
                          AND LOWER(region) = '(all)'
                          AND LOWER(genre)  = ?
                        ORDER BY month
                    """
                    rows = con.execute(fallback_sql, [as_of, genre]).fetchall()
                    items = _select_closest_to_mean(rows)

                # 2차 fallback: (ALL, ALL)
                if not items:
                    fallback_sql2 = """
                        SELECT month, forecast, yhat_lower, yhat_upper
                        FROM analytics.demand_forecast_asof
                        WHERE as_of_month = CAST(? AS DATE)
                          AND LOWER(region) = '(all)'
                          AND LOWER(genre)  = '(all)'
                        ORDER BY month
                    """
                    rows = con.execute(fallback_sql2, [as_of]).fetchall()
                    items = _select_closest_to_mean(rows)
        except Exception as e:
            return bad_request(f"DuckDB 조회 중 오류: {e}", "duckdb")

        if not items:
            return bad_request("해당 조합의 예측 결과가 없습니다.", "filters")
>>>>>>> c9f3e1d6b67b82bbf25fdbcdb82ff91a384c848f

        return Response({
            "region": raw_region,
            "genre": raw_genre,
<<<<<<< HEAD
            "age_group": (
                "전체" if (ag["mode"]=="value" and ag["value"]==-1)
                else ("미상" if ag["mode"]=="unknown" else (ag["value"] if ag["mode"]=="value" else None))
            ),
            "gender": (
                "전체" if (gd["mode"]=="value" and gd["value"]==-1)
                else ("알 수 없음" if (gd["mode"]=="value" and gd["value"]==0) else (self._gender_label(gd["value"]) if gd["mode"]=="value" else None))
            ),
=======
            "age_group": ag.get("value"),
            "gender": self._gender_label(gd.get("value")),
>>>>>>> c9f3e1d6b67b82bbf25fdbcdb82ff91a384c848f
            "as_of": as_of,
            "items": items
        })

<<<<<<< HEAD

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
=======
    # ------------------ 2. Shortage ------------------
    @swagger_auto_schema(
        operation_summary="공급 부족 지수 조회",
        operation_description="공급 부족 지수(=예측 구간폭 평균)를 반환합니다.",
>>>>>>> c9f3e1d6b67b82bbf25fdbcdb82ff91a384c848f
        tags=["Demand"]
    )
    @action(detail=False, methods=["get"])
    def shortage(self, request):
        raw_region = request.query_params.get("region")
        raw_genre  = request.query_params.get("genre")
        region = self._normalize(raw_region)
        genre  = self._normalize(raw_genre)
<<<<<<< HEAD
        as_of  = request.query_params.get("as_of") or "2025-09-01"

        if not region or not genre:
            return bad_request("region과 genre는 필수입니다.", "region/genre")
        try:
            sql = """
                SELECT shortage_index
                FROM analytics.shortage_index_asof
                WHERE as_of_month = DATE ?
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
=======
        as_of  = request.query_params.get("as_of")

        if not region or not genre:
            return bad_request("region과 genre는 필수입니다.", "region/genre")
>>>>>>> c9f3e1d6b67b82bbf25fdbcdb82ff91a384c848f

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

        return Response({"region": raw_region, "genre": raw_genre, "as_of": as_of, "shortage_index": shortage_index})

    # ------------------ 3. Recommendation ------------------
    @swagger_auto_schema(
        operation_summary="추천 지역/장르 조회",
        operation_description="특정 장르 → 인기 지역 TOP-N, 특정 지역 → 인기 장르 TOP-N 반환.",
        manual_parameters=[
<<<<<<< HEAD
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
=======
            openapi.Parameter("region", openapi.IN_QUERY, type=openapi.TYPE_STRING,
                              description="지역 (서울특별시 등). (ALL) 금지", required=False),
            openapi.Parameter("genre", openapi.IN_QUERY, type=openapi.TYPE_STRING,
                              description=f"장르명 {GENRE_CHOICES}. (ALL) 금지", required=False),
            openapi.Parameter("top_n", openapi.IN_QUERY, type=openapi.TYPE_INTEGER,
                              description="상위 N개 (기본값 3)", required=False),
        ],
>>>>>>> c9f3e1d6b67b82bbf25fdbcdb82ff91a384c848f
        tags=["Demand"]
    )
    @action(detail=False, methods=["get"])
    def recommendation(self, request):
        raw_region = request.query_params.get("region")
        raw_genre  = request.query_params.get("genre")
        region = self._normalize(raw_region) if raw_region else None
        genre  = self._normalize(raw_genre)  if raw_genre  else None

<<<<<<< HEAD
        # 하나만 전달 & (ALL) 금지
        if bool(region) == bool(genre):
            return bad_request("region 또는 genre 중 하나만 전달하세요.", "region/genre")
        if (raw_region and self._is_all(raw_region)) or (raw_genre and self._is_all(raw_genre)):
            return bad_request("추천 조회에서는 (ALL)을 사용할 수 없습니다. 구체 값을 전달하세요.", "region/genre")

        # top_n
=======
        if bool(region) == bool(genre):
            return bad_request("region 또는 genre 중 하나만 전달하세요.", "region/genre")

>>>>>>> c9f3e1d6b67b82bbf25fdbcdb82ff91a384c848f
        try:
            top_n = max(1, int(request.query_params.get("top_n", 3)))
        except ValueError:
            top_n = 3

        try:
            with get_duck_conn() as con:
<<<<<<< HEAD
                # 최신 월 기준 최근 3개월 경계
=======
>>>>>>> c9f3e1d6b67b82bbf25fdbcdb82ff91a384c848f
                bsql = """
                    WITH mx AS (
                        SELECT date_trunc('month', MAX(month)) AS end_month
                        FROM analytics.demand_modeling_grid
                    )
                    SELECT
<<<<<<< HEAD
                        (SELECT end_month FROM mx)                                  AS end_month,
                        ((SELECT end_month FROM mx) - INTERVAL 2 MONTH)             AS start_month,
                        ((SELECT end_month FROM mx) + INTERVAL 1 MONTH)             AS end_month_excl
                """
                end_month, start_month, end_month_excl = con.execute(bsql).fetchone()
                if not end_month:
                    return bad_request("analytics.demand_modeling_grid에 데이터가 없습니다.", "duckdb")

                if genre and not region:
                    # 장르 → 최근3개월 지역 TOP N (전체 레벨에서 집계: age_group=-1, gender=-1)
=======
                        (SELECT end_month FROM mx),
                        ((SELECT end_month FROM mx) - INTERVAL 2 MONTH),
                        ((SELECT end_month FROM mx) + INTERVAL 1 MONTH)
                """
                end_month, start_month, end_month_excl = con.execute(bsql).fetchone()

                if genre and not region:
>>>>>>> c9f3e1d6b67b82bbf25fdbcdb82ff91a384c848f
                    sql = f"""
                        SELECT region, SUM(demand) AS total_orders
                        FROM analytics.demand_modeling_grid
                        WHERE month >= ? AND month < ?
                          AND LOWER(genre) = ?
<<<<<<< HEAD
                          AND age_group = -1
                          AND gender    = -1
                          AND region IS NOT NULL
=======
                          AND age_group = -1 AND gender = -1
                          AND region IS NOT NULL
                          AND region NOT IN ('(ALL)', 'all')
>>>>>>> c9f3e1d6b67b82bbf25fdbcdb82ff91a384c848f
                        GROUP BY region
                        ORDER BY total_orders DESC NULLS LAST
                        LIMIT {top_n}
                    """
                    rows = con.execute(sql, [start_month, end_month_excl, genre]).fetchall()
<<<<<<< HEAD
                    results = [{"region": r[0], "total_orders": int(r[1]) if r[1] is not None else 0} for r in rows]
                    return Response({
                        "pivot": "by_genre",
                        "genre": raw_genre,  # 응답에 장르명 포함
=======
                    results = [{"region": r[0], "total_orders": int(r[1])} for r in rows]
                    return Response({
                        "pivot": "by_genre",
                        "genre": raw_genre,
>>>>>>> c9f3e1d6b67b82bbf25fdbcdb82ff91a384c848f
                        "period": {"start_month": str(start_month)[:10], "end_month": str(end_month)[:10]},
                        "top_n": top_n,
                        "results": results
                    })

                if region and not genre:
<<<<<<< HEAD
                    # 지역 → 최근3개월 장르 TOP N (전체 레벨에서 집계)
=======
>>>>>>> c9f3e1d6b67b82bbf25fdbcdb82ff91a384c848f
                    sql = f"""
                        SELECT genre, SUM(demand) AS total_orders
                        FROM analytics.demand_modeling_grid
                        WHERE month >= ? AND month < ?
                          AND LOWER(region) = ?
<<<<<<< HEAD
                          AND age_group = -1
                          AND gender    = -1
                          AND genre IS NOT NULL
=======
                          AND age_group = -1 AND gender = -1
                          AND genre IS NOT NULL
                          AND genre NOT IN ('(ALL)', 'all')
>>>>>>> c9f3e1d6b67b82bbf25fdbcdb82ff91a384c848f
                        GROUP BY genre
                        ORDER BY total_orders DESC NULLS LAST
                        LIMIT {top_n}
                    """
                    rows = con.execute(sql, [start_month, end_month_excl, region]).fetchall()
<<<<<<< HEAD
                    results = [{"genre": r[0], "total_orders": int(r[1]) if r[1] is not None else 0} for r in rows]
                    return Response({
                        "pivot": "by_region",
                        "region": raw_region,  
=======
                    results = [{"genre": r[0], "total_orders": int(r[1])} for r in rows]
                    return Response({
                        "pivot": "by_region",
                        "region": raw_region,
>>>>>>> c9f3e1d6b67b82bbf25fdbcdb82ff91a384c848f
                        "period": {"start_month": str(start_month)[:10], "end_month": str(end_month)[:10]},
                        "top_n": top_n,
                        "results": results
                    })
<<<<<<< HEAD

        except Exception as e:
            return bad_request(f"DuckDB 조회 중 오류: {e}", "duckdb")
=======
        except Exception as e:
            return bad_request(f"DuckDB 조회 중 오류: {e}", "duckdb")
>>>>>>> c9f3e1d6b67b82bbf25fdbcdb82ff91a384c848f
