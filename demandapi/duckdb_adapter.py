# -*- coding: utf-8 -*-
import os
import duckdb
from contextlib import contextmanager

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

ENV_PATH = os.environ.get("DUCKDB_ANALYTICS_DB")
CANDIDATES = [
    ENV_PATH,
    os.path.join(DATA_DIR, "testout6.duckdb"),
    os.path.join(DATA_DIR, "testout4.duckdb"),
]
DUCK_PATH = next((p for p in CANDIDATES if p and os.path.exists(p)),
                 os.path.join(DATA_DIR, "testout4.duckdb"))

@contextmanager
def get_duck_conn():
    con = duckdb.connect(DUCK_PATH, read_only=True)
    try:
        con.execute("PRAGMA threads=6; PRAGMA memory_limit='2GB';")
        yield con
    finally:
        con.close()

def _latest_asof(con) -> str | None:
    row = con.execute("SELECT MAX(as_of_month) FROM analytics.demand_forecast_asof").fetchone()
    return None if not row or not row[0] else str(row[0])[:10]

def get_forecast(region=None, genre=None, age_group=None, gender=None, as_of=None):
    try:
        with get_duck_conn() as con:
            if not as_of:
                as_of = _latest_asof(con)
                if not as_of:
                    return []

            where, params = [], []

            # ✅ as_of 월 기준 매칭
            where.append("DATE_TRUNC('month', as_of_month) = DATE_TRUNC('month', DATE ?)")
            params.append(as_of)

            # ✅ region
            if region is None:
                where.append("region IS NULL")
            elif str(region).strip().upper() == "(ALL)":
                where.append("LOWER(region)='(all)'")
            else:
                where.append("LOWER(region)=?")
                params.append(str(region).strip().lower())

            # ✅ genre
            if genre is None:
                where.append("genre IS NULL")
            elif str(genre).strip().upper() == "(ALL)":
                where.append("LOWER(genre)='(all)'")
            else:
                where.append("LOWER(genre)=?")
                params.append(str(genre).strip().lower())

            # ✅ age_group
            if age_group is None:
                where.append("age_group IS NULL")
            else:
                where.append("age_group = ?")
                params.append(int(age_group))

            # ✅ gender
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
    except Exception as e:
        print(f"[DuckDB ERROR] get_forecast failed: {e}")
        return []
