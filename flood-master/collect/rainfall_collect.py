# collect/rainfall_collect.py
import requests
import pandas as pd
from datetime import datetime, timedelta
import os
import sys
import time
import concurrent.futures

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import WEATHER_API_KEY, RAINFALL_DIR

GRID_FILE = os.path.join(RAINFALL_DIR, "기상청41_단기예보 조회서비스_오픈API활용가이드_격자_위경도(2510).xlsx")


# ── 서울 격자 좌표 로드 ────────────────────────────────────
def load_seoul_grid():
    df = pd.read_excel(GRID_FILE)
    seoul = df[df['1단계'] == '서울특별시'][
        ['1단계', '2단계', '3단계', '격자 X', '격자 Y']
    ].reset_index(drop=True)
    print(f"서울 격자 수: {len(seoul)}개")
    return seoul


# ── 기상청 단기예보 API 호출 (격자 1개) ───────────────────
def get_rainfall(base_date, base_time, nx, ny):
    url = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtFcst"
    params = {
        "serviceKey": WEATHER_API_KEY,
        "pageNo": 1,
        "numOfRows": 1000,
        "dataType": "JSON",
        "base_date": base_date,
        "base_time": base_time,
        "nx": nx,
        "ny": ny,
    }
    try:
        res = requests.get(url, params=params, timeout=10)
        if res.status_code == 200:
            items = res.json().get("response", {}).get("body", {}).get("items", {}).get("item", [])
            for item in items:
                if item.get("category") == "RN1":
                    return item.get("fcstValue", None)
    except Exception:
        pass
    return None


# ── 병렬 수집 공통 로직 ────────────────────────────────────
def collect_rainfall(base_date, base_time, max_workers=20):
    seoul_grid = load_seoul_grid()

    def fetch_one(row_tuple):
        _, row = row_tuple
        nx, ny = int(row['격자 X']), int(row['격자 Y'])
        rn1 = get_rainfall(base_date, base_time, nx, ny)
        return {
            "BASE_DATE": base_date,
            "BASE_TIME": base_time,
            "SIDO": row['1단계'],
            "SGG":  row['2단계'],
            "UMD":  row['3단계'],
            "NX":   nx,
            "NY":   ny,
            "RN1":  rn1,
        }

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(fetch_one, seoul_grid.iterrows()))

    return pd.DataFrame(results)


# ── 학습 데이터용 (기간 지정) ─────────────────────────────
def collect_train(start_date, end_date):
    print(f"\n[강우량 학습 데이터 수집] {start_date} ~ {end_date}")

    current = datetime.strptime(start_date, "%Y%m%d")
    end     = datetime.strptime(end_date,   "%Y%m%d")
    all_data = []

    while current <= end:
        for hour in range(24):
            base_date = current.strftime("%Y%m%d")
            base_time = f"{hour:02d}30"
            print(f"  수집 중: {base_date} {base_time}")
            df = collect_rainfall(base_date, base_time)
            all_data.append(df)
            time.sleep(0.1)
        current += timedelta(days=1)

    result = pd.concat(all_data, ignore_index=True)
    filename = os.path.join(RAINFALL_DIR, f"rainfall_{start_date}_{end_date}.csv")
    result.to_csv(filename, index=False, encoding="utf-8-sig")
    print(f"저장 완료: {filename} ({len(result)}행)")
    return result


# ── 실시간용 (현재 시각 1개만 수집) ───────────────────────
def collect_realtime():
    now = datetime.now()

    # 가장 최근 정각 30분 기준 시각 1개만 수집 (기존 3개 → 1개로 단축)
    if now.minute >= 30:
        base_time = f"{now.hour:02d}30"
    else:
        prev_hour = (now - timedelta(hours=1)).hour
        base_time = f"{prev_hour:02d}30"

    base_date = now.strftime("%Y%m%d")
    print(f"  수집 중: {base_date} {base_time} (병렬 수집)")

    result = collect_rainfall(base_date, base_time, max_workers=20)

    filename = os.path.join(RAINFALL_DIR, "rainfall_realtime.csv")
    result.to_csv(filename, index=False, encoding="utf-8-sig")
    print(f"저장 완료: {filename} ({len(result)}행)")
    return result
