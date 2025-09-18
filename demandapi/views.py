import duckdb
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .duckdb_adapter import get_forecast, get_duck_conn

DB_PATH = "/opt/render/project/src/data/testout5.duckdb"

def bad_request(detail: str, field: str = ""):
    payload = {"detail": detail, "code": "invalid_param"}
    if field:
        payload["field"] = field
    return Response(payload, status=400)

class DemandViewSet(viewsets.ViewSet):
    def _normalize(self, value: str):
        if not value:
            return None
        return value.strip()

    def _is_all(self, value: str) -> bool:
        return str(value).strip().lower() in {"all", "(all)"}

    # age_group: -1=전체, 미상=IS NULL, 숫자(10/20/..)=그 값
    def _parse_age_group2(self, value: str | None):
        if value is None or str(value).strip() == "":
            return {"mode": "unspecified", "value": None}
        v = str(value).strip()
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
        tags=["Demand"]
    )
    @action(detail=False, methods=["get"])
    def forecast(self, request):
        raw_region = request.query_params.get("region")
        raw_genre  = request.query_params.get("genre")
        if not raw_region or not raw_genre:
            return bad_request("region과 genre는 필수입니다.", "region/genre")

        ag = self._parse_age_group2(request.query_params.get("age_group"))
        gd = self._parse_gender2(request.query_params.get("gender"))
        if ag["mode"] == "invalid":
            return bad_request("age_group 형식이 올바르지 않습니다. (-1/10/20/.../미상)", "age_group")
        if gd["mode"] == "invalid":
            return bad_request("gender 형식이 올바르지 않습니다. (-1/0/1/2/미상)", "gender")

        as_of = request.query_params.get("as_of")

        try:
            with get_duck_conn() as con:
                # as_of가 없으면 최신 값으로 대체
                if not as_of:
                    as_of = con.execute("SELECT MAX(as_of_month) FROM analytics.demand_forecast_asof").fetchone()[0]

                sql = """
                    SELECT month, forecast, yhat_lower, yhat_upper
                    FROM analytics.demand_forecast_asof
                    WHERE region = ? AND genre = ? AND as_of_month = ?
                """
                rows = con.execute(sql, [raw_region, raw_genre, as_of]).fetchall()
        except duckdb.Error as e:
            return bad_request(f"DuckDB 연결/쿼리 오류: {e}", "duckdb")

        items = [{
            "month": str(r[0]),
            "forecast": r[1],
            "yhat_lower": r[2],
            "yhat_upper": r[3],
        } for r in rows]

        if not items:
            return bad_request("해당 조합의 예측 결과가 없습니다.", "filters")

        return Response({
            "region": raw_region,
            "genre": raw_genre,
            "age_group": str(ag.get("value")) if ag["mode"]=="value" else None,
            "gender": self._gender_label(gd.get("value")) if gd["mode"]=="value" else None,
            "as_of": str(as_of),
            "items": items
        })


    @swagger_auto_schema(
        operation_summary="공급 부족 지수 조회",
        operation_description="지역, 장르별 공급 부족 지수를 반환합니다.",
        tags=["Demand"]
    )
    @action(detail=False, methods=["get"])
    def shortage(self, request):
        raw_region = request.query_params.get("region")
        raw_genre  = request.query_params.get("genre")
        as_of  = request.query_params.get("as_of")

        if not raw_region or not raw_genre:
            return bad_request("region과 genre는 필수입니다.", "region/genre")

        try:
            with get_duck_conn() as con:
                if not as_of:
                    as_of = con.execute("SELECT MAX(as_of_month) FROM analytics.demand_forecast_asof").fetchone()[0]
                # shortage_index 없으므로 yhat_upper - yhat_lower를 proxy로 사용
                sql = """
                    SELECT AVG(yhat_upper - yhat_lower) AS shortage_index
                    FROM analytics.demand_forecast_asof
                    WHERE region = ? AND genre = ? AND as_of_month = ?
                """
                rec = con.execute(sql, [raw_region, raw_genre, as_of]).fetchone()
            if not rec or rec[0] is None:
                return bad_request("해당 조건의 shortage_index가 없습니다.", "region/genre/as_of")
        except duckdb.Error as e:
            return bad_request(f"DuckDB 연결/쿼리 오류: {e}", "duckdb")

        return Response({
            "region": raw_region,
            "genre": raw_genre,
            "as_of": str(as_of),
            "shortage_index": rec[0]
        })


    @swagger_auto_schema(
        operation_summary="추천 지역/장르 조회",
        operation_description="입력된 지역 또는 장르를 기반으로 추천 지역/장르를 반환합니다.",
        tags=["Demand"]
    )
    @action(detail=False, methods=["get"])
    def recommendation(self, request):
        raw_region = request.query_params.get("region")
        raw_genre  = request.query_params.get("genre")
        top_n = int(request.query_params.get("top_n", 3))

        if bool(raw_region) == bool(raw_genre):
            return bad_request("region 또는 genre 중 하나만 전달하세요.", "region/genre")

        try:
            with get_duck_conn() as con:
                # 최신 월 기준 최근 3개월
                bsql = """
                    WITH mx AS (
                        SELECT date_trunc('month', MAX(month)) AS end_month
                        FROM analytics.demand_modeling_grid
                    )
                    SELECT
                        (SELECT end_month FROM mx) AS end_month,
                        ((SELECT end_month FROM mx) - INTERVAL 2 MONTH) AS start_month,
                        ((SELECT end_month FROM mx) + INTERVAL 1 MONTH) AS end_month_excl
                """
                end_month, start_month, end_month_excl = con.execute(bsql).fetchone()

                if raw_genre and not raw_region:
                    sql = f"""
                        SELECT region, SUM(demand) AS total_orders
                        FROM analytics.demand_modeling_grid
                        WHERE month >= ? AND month < ? AND genre = ?
                        GROUP BY region
                        ORDER BY total_orders DESC NULLS LAST
                        LIMIT {top_n}
                    """
                    rows = con.execute(sql, [start_month, end_month_excl, raw_genre]).fetchall()
                    results = [{"region": r[0], "total_orders": int(r[1])} for r in rows]

                    return Response({
                        "pivot": "by_genre",
                        "genre": raw_genre,
                        "period": {"start_month": str(start_month)[:10], "end_month": str(end_month)[:10]},
                        "top_n": top_n,
                        "results": results
                    })

                if raw_region and not raw_genre:
                    sql = f"""
                        SELECT genre, SUM(demand) AS total_orders
                        FROM analytics.demand_modeling_grid
                        WHERE month >= ? AND month < ? AND region = ?
                        GROUP BY genre
                        ORDER BY total_orders DESC NULLS LAST
                        LIMIT {top_n}
                    """
                    rows = con.execute(sql, [start_month, end_month_excl, raw_region]).fetchall()
                    results = [{"genre": r[0], "total_orders": int(r[1])} for r in rows]

                    return Response({
                        "pivot": "by_region",
                        "region": raw_region,
                        "period": {"start_month": str(start_month)[:10], "end_month": str(end_month)[:10]},
                        "top_n": top_n,
                        "results": results
                    })

        except duckdb.Error as e:
            return bad_request(f"DuckDB 연결/쿼리 오류: {e}", "duckdb")

def _clean_json(obj):
    import numpy as np
    if isinstance(obj, dict):
        return {k: _clean_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_clean_json(v) for v in obj]
    elif isinstance(obj, float):
        if np.isnan(obj) or np.isinf(obj):
            return None
    return obj
