# collect/drainpipe_collect.py
import xml.etree.ElementTree as ET
import re
import time
import requests
import pandas as pd
from datetime import datetime, timedelta
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import SEOUL_API_KEY, KAKAO_API_KEY, DISTRICT_CODES, DRAINPIPE_DIR, PROCESSED_DIR, MASTER_FILE


# ── 주소 정제 ──────────────────────────────────────────────
def extract_address(pstn_info):
    text = str(pstn_info).strip()
    
    # 오타 수정
    text = text.replace('중로구', '종로구')
    
    # 괄호/꺾쇠 안 내용 제거
    text = re.sub(r'[\(\<\[].+?[\)\>\]]', '', text).strip()
    
    # 줄바꿈 제거
    text = re.sub(r'\n', ' ', text).strip()
    
    # 지하 주소 제거 (지하189 같은 것)
    text = re.sub(r'\s*지하\d+', '', text).strip()
    
    # 범위 표현 제거 (서운로164~서운로162사이 → 서운로164)
    text = re.sub(r'~.+', '', text).strip()
    
    # "앞", "뒤", "옆" 등 이후 제거
    text = re.sub(r'\s*(앞|뒤|옆|맨홀|도로변|사거리|교통섬|주변|진입로|정문|보도|도로|골목|천장|우측|좌측|남쪽|북쪽|동쪽|서쪽|남서쪽|남동쪽|북서쪽|북동쪽).*$', '', text).strip()
    
    # 숫자m 거리 표현 제거 (60m, 30m 등)
    text = re.sub(r'\d+m.*$', '', text).strip()
    
    # 서울특별시 없으면 앞에 붙이기
    if not text.startswith('서울'):
        text = '서울특별시 ' + text
    
    return text


# ── 카카오 지오코딩 ────────────────────────────────────────
def geocode(addr):
    url = "https://dapi.kakao.com/v2/local/search/address.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    params = {"query": addr, "analyze_type": "similar"}
    try:
        res = requests.get(url, headers=headers, params=params, timeout=10)
        if res.status_code == 200:
            docs = res.json().get("documents", [])
            if docs:
                return float(docs[0]["y"]), float(docs[0]["x"])
    except Exception as e:
        print(f"지오코딩 실패 ({addr}): {e}")
    return None, None


# ── 위치 마스터 업데이트 (신규 UNQ_NO만 지오코딩) ──────────
def update_master(df):
    if os.path.exists(MASTER_FILE):
        master = pd.read_csv(MASTER_FILE, encoding="utf-8-sig")
    else:
        master = pd.DataFrame(columns=['UNQ_NO', 'SE_CD', 'SE_NM', 'PSTN_INFO', 'CLEANED_ADDR', 'LAT', 'LON'])

    location_df = df[['UNQ_NO', 'SE_CD', 'SE_NM', 'PSTN_INFO']].drop_duplicates(subset='UNQ_NO')
    new_df = location_df[~location_df['UNQ_NO'].isin(master['UNQ_NO'])].reset_index(drop=True)

    if new_df.empty:
        print("신규 관측소 없음 - 지오코딩 스킵")
        return master

    print(f"신규 관측소 {len(new_df)}개 지오코딩 시작")
    new_rows = []
    for _, row in new_df.iterrows():
        cleaned = extract_address(row['PSTN_INFO'])
        lat, lon = geocode(cleaned)
        new_rows.append({
            'UNQ_NO': row['UNQ_NO'],
            'SE_CD': row['SE_CD'],
            'SE_NM': row['SE_NM'],
            'PSTN_INFO': row['PSTN_INFO'],
            'CLEANED_ADDR': cleaned,
            'LAT': lat,
            'LON': lon,
        })
        print(f"  [{row['UNQ_NO']}] {cleaned} → ({lat}, {lon})")
        time.sleep(0.1)

    master = pd.concat([master, pd.DataFrame(new_rows)], ignore_index=True)
    master.to_csv(MASTER_FILE, index=False, encoding="utf-8-sig")
    print(f"마스터 업데이트 완료 (총 {len(master)}개)")
    return master


# ── 서울시 API 수집 ────────────────────────────────────────
def collect_drainpipe(start_dt, end_dt):
    parsed_data = []

    for code in DISTRICT_CODES:
        print(f"[지역코드 {code}] 수집 시작")
        start = 1
        end = 1000

        while True:
            url = f"http://openAPI.seoul.go.kr:8088/{SEOUL_API_KEY}/xml/DrainpipeMonitoringInfo/{start}/{end}/{code}/{start_dt}/{end_dt}"

            try:
                response = requests.get(url, timeout=10)
                if response.status_code != 200:
                    print(f"[{code}] 오류 (Status: {response.status_code})")
                    break

                root = ET.fromstring(response.text)
                total_count_tag = root.find(".//list_total_count")

                if total_count_tag is None or total_count_tag.text is None:
                    break

                total_count = int(total_count_tag.text)
                rows = root.findall(".//row")

                for row in rows:
                    parsed_data.append({child.tag: child.text for child in row})

                print(f"[{code}] 구간 {start}~{end} 완료 ({len(rows)} / {total_count})")

                if end >= total_count:
                    break

                start += 1000
                end += 1000
                time.sleep(0.1)

            except Exception as e:
                print(f"[{code}] 에러: {e}")
                break

    return pd.DataFrame(parsed_data) if parsed_data else pd.DataFrame()


# ── 학습 데이터용 (기간 지정) ─────────────────────────────
def collect_train(start_dt, end_dt):
    print(f"\n[학습 데이터 수집] {start_dt} ~ {end_dt}")
    df = collect_drainpipe(start_dt, end_dt)
    if df.empty:
        print("수집된 데이터 없음")
        return

    master = update_master(df)
    result = df.merge(master[['UNQ_NO', 'CLEANED_ADDR', 'LAT', 'LON']], on='UNQ_NO', how='left')

    filename = os.path.join(DRAINPIPE_DIR, f"drainpipe_{start_dt}_{end_dt}.csv")
    result.to_csv(filename, index=False, encoding="utf-8-sig")
    print(f"저장 완료: {filename} ({len(result)}행)")
    return result


# ── 실시간용 (항상 최신 3시간치로 덮어쓰기) ───────────────
def collect_realtime():
    now = datetime.now()
    three_hours_ago = now - timedelta(hours=3)
    start_dt = three_hours_ago.strftime("%Y%m%d%H")
    end_dt = now.strftime("%Y%m%d%H")

    print(f"\n[실시간 수집] {now.strftime('%Y-%m-%d %H:%M')}")
    df = collect_drainpipe(start_dt, end_dt)
    if df.empty:
        print("수집된 데이터 없음")
        return

    master = update_master(df)
    result = df.merge(master[['UNQ_NO', 'CLEANED_ADDR', 'LAT', 'LON']], on='UNQ_NO', how='left')

    # 항상 같은 파일명으로 덮어쓰기 (최신 3시간치만 유지)
    filename = os.path.join(DRAINPIPE_DIR, "drainpipe_realtime.csv")
    result.to_csv(filename, index=False, encoding="utf-8-sig")
    print(f"저장 완료: {filename} ({len(result)}행)")
    return result