# fix_master.py
import pandas as pd
import requests
import re
import time
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import KAKAO_API_KEY, MASTER_FILE


# ── 수동 주소 매핑 ─────────────────────────────────────────
MANUAL_ADDR = {
    '12-0001': '서울특별시 은평구 수색로 257',
    '14-0009': '서울특별시 마포구 서강로 119',
    '16-0017': '서울특별시 강서구 방화동 751-6',
    '17-0013': '서울특별시 구로구 개봉동 416-225',
    '17-0016': '서울특별시 구로구 개봉동 438',
    '22-0008': '서울특별시 서초구 방배중앙로 121',
    '23-0007': '서울특별시 강남구 압구정동 성수대교남단교차로',
    '23-0018': '서울특별시 강남구 일원동',
}

# ── 수동 좌표 매핑 ─────────────────────────────────────────
MANUAL_COORDS = {
    '12-0001': (37.58194719999999, 126.895252),
    '16-0017': (37.5840152, 126.8193656),
    '17-0013': (37.4958418, 126.8572212),
    '23-0007': (37.5291721738221, 127.033754555012),
}


# ── 개선된 주소 정제 ───────────────────────────────────────
def extract_address(pstn_info):
    text = str(pstn_info).strip()

    # 오타 수정
    text = text.replace('중로구', '종로구')

    # 괄호/꺾쇠 안 내용 제거
    text = re.sub(r'[\(\<\[].+?[\)\>\]]', '', text).strip()

    # 줄바꿈 제거
    text = re.sub(r'\n', ' ', text).strip()

    # 지하 주소 제거
    text = re.sub(r'\s*지하\d+', '', text).strip()

    # 범위 표현 제거
    text = re.sub(r'~.+', '', text).strip()

    # 도로명 + 숫자 뒤 건물명/부가설명 제거
    text = re.sub(r'(\d+길|\d+로|\d+대로)(\s+\S.*)?$', r'\1', text).strip()

    # "앞", "뒤" 등 이후 제거
    text = re.sub(
        r'\s*(앞|뒤|옆|맨홀|도로변|사거리|교통섬|주변|진입로|정문|보도|도로|골목|천장|우측|좌측|남쪽|북쪽|동쪽|서쪽|남서쪽|남동쪽|북서쪽|북동쪽).*$',
        '', text
    ).strip()

    # 숫자m 거리 표현 제거
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


# ── 카카오 키워드 검색 (fallback) ──────────────────────────
def geocode_keyword(addr):
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    params = {"query": addr}
    try:
        res = requests.get(url, headers=headers, params=params, timeout=10)
        if res.status_code == 200:
            docs = res.json().get("documents", [])
            if docs:
                return float(docs[0]["y"]), float(docs[0]["x"])
    except Exception as e:
        print(f"키워드 검색 실패 ({addr}): {e}")
    return None, None


# ── None 좌표 재시도 ───────────────────────────────────────
def fix_master():
    print("\n[location_master None 좌표 재시도]")

    master = pd.read_csv(MASTER_FILE, encoding="utf-8-sig")
    none_df = master[master['LAT'].isna()].copy()
    print(f"None 좌표 수: {len(none_df)}개")

    for idx, row in none_df.iterrows():
        unq_no = row['UNQ_NO']

        # 수동 좌표 우선 적용
        if unq_no in MANUAL_COORDS:
            lat, lon = MANUAL_COORDS[unq_no]
            cleaned = MANUAL_ADDR.get(unq_no, row['CLEANED_ADDR'])
            print(f"  [{unq_no}] 수동 좌표 적용 → ({lat}, {lon})")
        else:
            cleaned = MANUAL_ADDR.get(unq_no, extract_address(row['PSTN_INFO']))
            lat, lon = geocode(cleaned)

            if lat is None:
                print(f"  [{unq_no}] 주소 검색 실패 → 키워드 검색 시도")
                lat, lon = geocode_keyword(cleaned)

            status = f"({lat}, {lon})" if lat else "여전히 None"
            print(f"  [{unq_no}] {cleaned} → {status}")

        master.at[idx, 'CLEANED_ADDR'] = cleaned
        master.at[idx, 'LAT'] = lat
        master.at[idx, 'LON'] = lon
        time.sleep(0.1)

    master.to_csv(MASTER_FILE, index=False, encoding="utf-8-sig")

    remaining = master['LAT'].isna().sum()
    print(f"\n저장 완료: {MASTER_FILE}")
    print(f"여전히 None: {remaining}개")
    return master


if __name__ == "__main__":
    fix_master()