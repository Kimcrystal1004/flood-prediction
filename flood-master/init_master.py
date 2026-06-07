# init_master.py
import pandas as pd
import requests
import re
import time
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import KAKAO_API_KEY, MASTER_FILE, DRAINPIPE_DIR


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


# ── 마스터 초기 생성 ───────────────────────────────────────
def init_master(csv_path):
    print(f"\n[location_master 초기 생성 시작]")
    print(f"기준 파일: {csv_path}")

    # 헤더 자동 감지
    try:
        df = pd.read_csv(csv_path, encoding="utf-8-sig")
        if 'UNQ_NO' not in df.columns:
            raise ValueError("컬럼명 없음")
    except:
        df = pd.read_csv(csv_path, encoding="utf-8-sig", header=None)
        df.columns = ['UNQ_NO', 'SE_CD', 'SE_NM', 'MSRMT_YMD', 'MSRMT_WATL', 'SGN_STTS', 'PSTN_INFO']

    # 헤더가 데이터로 들어간 경우 제거
    df = df[df['UNQ_NO'] != 'UNQ_NO'].reset_index(drop=True)

    # UNQ_NO 기준 중복 제거
    location_df = df[['UNQ_NO', 'SE_CD', 'SE_NM', 'PSTN_INFO']].drop_duplicates(subset='UNQ_NO').reset_index(drop=True)
    print(f"총 관측소 수: {len(location_df)}개")

    # 기존 마스터 있으면 신규만 처리
    if os.path.exists(MASTER_FILE):
        existing = pd.read_csv(MASTER_FILE, encoding="utf-8-sig")
        # 잘못 들어간 헤더 행 제거
        existing = existing[existing['UNQ_NO'] != 'UNQ_NO'].reset_index(drop=True)
        location_df = location_df[~location_df['UNQ_NO'].isin(existing['UNQ_NO'])].reset_index(drop=True)
        print(f"신규 관측소: {len(location_df)}개 (기존 마스터 존재)")
        if location_df.empty:
            print("추가할 관측소 없음")
            # 기존 마스터 정제 후 재저장
            existing.to_csv(MASTER_FILE, index=False, encoding="utf-8-sig")
            return existing
    else:
        existing = pd.DataFrame(columns=['UNQ_NO', 'SE_CD', 'SE_NM', 'PSTN_INFO', 'CLEANED_ADDR', 'LAT', 'LON'])

    new_rows = []
    for i, row in location_df.iterrows():
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
        print(f"  [{i+1}/{len(location_df)}] [{row['UNQ_NO']}] {cleaned} → ({lat}, {lon})")
        time.sleep(0.1)

    master = pd.concat([existing, pd.DataFrame(new_rows)], ignore_index=True)
    master.to_csv(MASTER_FILE, index=False, encoding="utf-8-sig")
    print(f"\n저장 완료: {MASTER_FILE} (총 {len(master)}개)")
    return master


if __name__ == "__main__":
    csv_path = os.path.join(DRAINPIPE_DIR, "서울시_하수관로_2026052318.csv")
    init_master(csv_path)