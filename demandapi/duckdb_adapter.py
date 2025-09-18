# demandapi/duckdb_adapter.py
# -*- coding: utf-8 -*-
import os
import duckdb
from contextlib import contextmanager

# === DuckDB 경로 결정 ===
# 1) 환경변수 DUCKDB_ANALYTICS_DB 우선
# 2) BASE_DIR/data/testout5.duckdb 있으면 그걸 사용
# 3) 없으면 BASE_DIR/data/testout4.duckdb 사용
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

ENV_PATH = os.environ.get("DUCKDB_ANALYTICS_DB")
CANDIDATES = [
    ENV_PATH,
    os.path.join(DATA_DIR, "testout5.duckdb"),
    os.path.join(DATA_DIR, "testout4.duckdb"),
]
DUCK_PATH = next((p for p in CANDIDATES if p and os.path.exists(p)), os.path.join(DATA_DIR, "testout4.duckdb"))

@contextmanager
def get_duck_conn():
    """DuckDB 연결을 context manager로 열고 닫음 (READ ONLY)"""
    con = duckdb.connect(DUCK_PATH, read_only=True)
    try:
        con.execute("PRAGMA threads=6; PRAGMA memory_limit='2GB';")
        yield con
    finally:
        con.close()

def _latest_asof(con) -> str | None:
    """analytics.demand_forecast_asof에서 최신 as_of_month를 YYYY-MM-01 문자열로 반환"""
    row = con.execute("SELECT MAX(as_of_month) FROM analytics.demand_forecast_asof").fetchone()
    return None if not row or not row[0] else str(row[0])[:10]

def get_forecast(region=None, genre=None, age_group=None, gender=None, as_of=None):
    """
    조건별 forecast 결과 조회 (list[dict] 반환)

    필터 규칙:
      - region / genre: '(ALL)' 문자열을 값으로 사용 가능 (소문자 비교)
                        None이면 IS NULL 비교
      - age_group:     -1 → 전체 레벨 → age_group = -1
                        None → 미상 → age_group IS NULL
                        그 외(10/20/.. 숫자) → age_group = 값
      - gender:        -1 → 전체 레벨 → gender = -1
                        0  → 미상 → gender = 0
                        1/2 → gender = 값
                        None → (예측 테이블 정책상 일반적으로 없지만) IS NULL 비교
      - as_of:         None이면 최신 스냅샷(최대 as_of_month) 자동 선택

    반환 컬럼:
      region, genre, age_group, gender, month, forecast, yhat_lower, yhat_upper
    """
    where = []
    params = []

    with get_duck_conn() as con:
        # as_of 자동선택
        if not as_of:
            as_of = _latest_asof(con)
            if not as_of:
                return []

        # as_of
        where.append("as_of_month = DATE ?")
        params.append(as_of)

        # region / genre: LOWER 비교, None은 IS NULL
        if region is None:
            where.append("region IS NULL")
        else:
            where.append("LOWER(region) = ?")
            params.append(str(region).strip().lower())

        if genre is None:
            where.append("genre IS NULL")
        else:
            where.append("LOWER(genre) = ?")
            params.append(str(genre).strip().lower())

        # age_group
        # -1(전체) → '='
        # None(미상) → IS NULL
        if age_group is None:
            where.append("age_group IS NULL")
        else:
            where.append("age_group = ?")
            params.append(int(age_group))

        # gender
        # -1/0/1/2 → '='
        # None → IS NULL
        if gender is None:
            where.append("gender IS NULL")
        else:
            where.append("gender = ?")
            params.append(int(gender))

        sql = f"""
            SELECT region, genre, age_group, gender, month, forecast, yhat_lower, yhat_upper
            FROM analytics.demand_forecast_asof
            WHERE {" AND ".join(where)}
            ORDER BY month
        """

        df = con.execute(sql, params).fetch_df()
        return df.to_dict(orient="records")
