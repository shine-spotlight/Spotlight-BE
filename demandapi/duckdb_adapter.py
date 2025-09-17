import os
import duckdb
from contextlib import contextmanager

# BASE_DIR = 프로젝트 루트 (manage.py 있는 위치)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DUCK_PATH = os.path.join(BASE_DIR, "data", "testout4.duckdb")

@contextmanager
def get_duck_conn():
    """DuckDB 연결을 context manager로 열고 닫음"""
    con = duckdb.connect(DUCK_PATH, read_only=True)
    try:
        con.execute("PRAGMA threads=6; PRAGMA memory_limit='2GB';")
        yield con
    finally:
        con.close()

def get_forecast(region=None, genre=None, age_group=None, gender=None, as_of="2025-09-01"):
    """조건별 forecast 결과 조회"""
    where = ["as_of_month = DATE ?"]
    params = [as_of]

    for col, val in [("region", region), ("genre", genre), ("age_group", age_group), ("gender", gender)]:
        if val is None:
            where.append(f"{col} IS NULL")
        else:
            where.append(f"{col} = ?")
            params.append(val)

    sql = f"""
        SELECT region, genre, age_group, gender, month, forecast, yhat_lower, yhat_upper
        FROM analytics.demand_forecast_asof
        WHERE {" AND ".join(where)}
        ORDER BY month
    """

    with get_duck_conn() as con:
        df = con.execute(sql, params).fetch_df()
        return df.to_dict(orient="records")
