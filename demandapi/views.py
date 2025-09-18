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
                items = [{
                    "month": str(r[0])[:10],
                    "forecast": r[1],
                    "yhat_lower": r[2],
                    "yhat_upper": r[3],
                } for r in (rows or [])]

                # Fallback 1: (ALL, genre)
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
                    items = [{
                        "month": str(r[0])[:10],
                        "forecast": r[1],
                        "yhat_lower": r[2],
                        "yhat_upper": r[3],
                    } for r in (rows or [])]
                    if not items:
                        # 2차 fallback: (ALL, ALL)
                        fallback_sql2 = """
                            SELECT month, forecast, yhat_lower, yhat_upper
                            FROM analytics.demand_forecast_asof
                            WHERE as_of_month = CAST(? AS DATE)
                              AND LOWER(region) = '(all)'
                              AND LOWER(genre)  = '(all)'
                            ORDER BY month
                        """
                        rows = con.execute(fallback_sql2, [as_of]).fetchall()
                        items = [{
                            "month": str(r[0])[:10],
                            "forecast": r[1],
                            "yhat_lower": r[2],
                            "yhat_upper": r[3],
                        } for r in (rows or [])]
        except Exception as e:
            return bad_request(f"DuckDB 조회 중 오류: {e}", "duckdb")

        if not items:
            return bad_request("해당 조합의 예측 결과가 없습니다.", "filters")

        return Response({
            "region": raw_region,
            "genre": raw_genre,
            "age_group": ag.get("value"),
            "gender": self._gender_label(gd.get("value")),
            "as_of": as_of,
            "items": items
        })

    # ------------------ 2. Shortage ------------------
    @swagger_auto_schema(
        operation_summary="공급 부족 지수 조회",
        tags=["Demand"]
    )
    @action(detail=False, methods=["get"])
    def shortage(self, request):
        raw_region = request.query_params.get("region")
        raw_genre  = request.query_params.get("genre")
        region = self._normalize(raw_region)
        genre  = self._normalize(raw_genre)
        as_of  = request.query_params.get("as_of")

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

        return Response({"region": raw_region, "genre": raw_genre, "as_of": as_of, "shortage_index": shortage_index})

    # ------------------ 3. Recommendation ------------------
    @swagger_auto_schema(
        operation_summary="추천 지역/장르 조회",
        tags=["Demand"]
    )
    @action(detail=False, methods=["get"])
    def recommendation(self, request):
        raw_region = request.query_params.get("region")
        raw_genre  = request.query_params.get("genre")
        region = self._normalize(raw_region) if raw_region else None
        genre  = self._normalize(raw_genre)  if raw_genre  else None

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
                        "period": {"start_month": str(start_month)[:10], "end_month": str(end_month)[:10]},
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
                        "period": {"start_month": str(start_month)[:10], "end_month": str(end_month)[:10]},
                        "top_n": top_n,
                        "results": results
                    })
        except Exception as e:
            return bad_request(f"DuckDB 조회 중 오류: {e}", "duckdb")
