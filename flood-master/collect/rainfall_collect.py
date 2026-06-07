# collect/rainfall_collect.py
import requests
import pandas as pd
from datetime import datetime, timedelta
import os
import sys
import time

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


# ── 기상청 단기예보 API 호출 ───────────────────────────────
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
    except Exception as e:
        print(f"강우량 API 실패 (nx={nx}, ny={ny}): {e}")
    return None


# ── 수집 공통 로직 ─────────────────────────────────────────
def collect_rainfall(base_date, base_time):
    seoul_grid = load_seoul_grid()
    results = []

    for _, row in seoul_grid.iterrows():
        nx, ny = int(row['격자 X']), int(row['격자 Y'])
        rn1 = get_rainfall(base_date, base_time, nx, ny)
        results.append({
            "BASE_DATE": base_date,
            "BASE_TIME": base_time,
            "SIDO": row['1단계'],
            "SGG": row['2단계'],
            "UMD": row['3단계'],
            "NX": nx,
            "NY": ny,
            "RN1": rn1,
        })
        time.sleep(0.05)

    return pd.DataFrame(results)


# ── 학습 데이터용 (기간 지정) ─────────────────────────────
def collect_train(start_date, end_date):
    """
    start_date, end_date: "20260101" 형식
    기상청 초단기예보는 매시 30분 발표 (0030, 0130, ... 2330)
    """
    print(f"\n[강우량 학습 데이터 수집] {start_date} ~ {end_date}")

    current = datetime.strptime(start_date, "%Y%m%d")
    end = datetime.strptime(end_date, "%Y%m%d")
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


# ── 실시간용 (현재 시각 기준) ─────────────────────────────
def collect_realtime():
    now = datetime.now()
    base_date = now.strftime("%Y%m%d")

    # 기상청 초단기예보 발표 시각: 매시 30분
    # 현재 시각 기준 가장 최근 발표 시각
    if now.minute >= 30:
        base_time = f"{now.hour:02d}30"
    else:
        prev_hour = (now - timedelta(hours=1)).hour
        base_time = f"{prev_hour:02d}30"

    print(f"\n[강우량 실시간 수집] {base_date} {base_time}")
    df = collect_rainfall(base_date, base_time)

    # 항상 같은 파일명으로 덮어쓰기 (최신 데이터만 유지)
    filename = os.path.join(RAINFALL_DIR, "rainfall_realtime.csv")
    df.to_csv(filename, index=False, encoding="utf-8-sig")
    print(f"저장 완료: {filename} ({len(df)}행)")
    return df