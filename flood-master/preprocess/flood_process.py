# preprocess/flood_process.py
import geopandas as gpd
import pandas as pd
import numpy as np
from zipfile import ZipFile
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import FLOOD_DIR, FLOOD_FILE, PROCESSED_DIR, BOUNDARY_DIR


SHP_FILE = os.path.join(BOUNDARY_DIR, "boundary_extracted", "LSMD_ADM_SECT_UMD_11_202605.shp")


# ── 1. 서울 행정경계 로드 ──────────────────────────────────
def load_boundary():
    boundary = gpd.read_file(SHP_FILE, encoding="euc-kr")
    boundary = boundary.to_crs("EPSG:4326")
    return boundary


# ── 2. zip 압축 해제 ───────────────────────────────────────
def extract_flood():
    extract_dir = os.path.join(FLOOD_DIR, "flood_extracted")
    if os.path.exists(extract_dir):
        print("이미 압축 해제됨 - 스킵")
        return extract_dir

    with ZipFile(FLOOD_FILE) as z:
        z.extractall(extract_dir)
    print("침수 흔적도 압축 해제 완료")
    return extract_dir


# ── 3. shp 파일 로드 ───────────────────────────────────────
def load_flood(extract_dir):
    shp_files = []
    for root, dirs, files in os.walk(extract_dir):
        for f in files:
            if f.endswith(".shp"):
                shp_files.append(os.path.join(root, f))

    if not shp_files:
        raise FileNotFoundError("shp 파일을 찾을 수 없어요")

    print(f"발견된 shp 파일:")
    for i, f in enumerate(shp_files):
        print(f"  [{i}] {f}")

    gdfs = []
    for shp in shp_files:
        try:
            gdf = gpd.read_file(shp, encoding="euc-kr")
            gdfs.append(gdf)
            print(f"로드 완료: {os.path.basename(shp)} ({len(gdf)}행)")
        except Exception as e:
            print(f"로드 실패: {shp} - {e}")

    if not gdfs:
        raise ValueError("로드된 shp 파일이 없어요")

    combined = pd.concat(gdfs, ignore_index=True)
    print(f"\n전체 합계: {len(combined)}행")
    return combined


# ── 4. 전처리 및 파생변수 생성 ─────────────────────────────
def process_flood(df):
    cols = ['F_SHIM', 'F_AREA', 'F_ZONE_NM', 'F_YR', 'geometry']
    existing_cols = [c for c in cols if c in df.columns]
    gdf = gpd.GeoDataFrame(df[existing_cols], geometry='geometry')

    gdf['F_SHIM'] = pd.to_numeric(gdf['F_SHIM'], errors='coerce')
    gdf['F_AREA'] = pd.to_numeric(gdf['F_AREA'], errors='coerce')
    gdf['F_YR']   = pd.to_numeric(gdf['F_YR'], errors='coerce')

    gdf = gdf.dropna(subset=['F_SHIM', 'F_AREA']).reset_index(drop=True)

    gdf['FLOOD_SCALE']          = gdf['F_SHIM'] * gdf['F_AREA']
    gdf['FLOOD_DEPTH_PER_AREA'] = gdf['F_SHIM'] / gdf['F_AREA']
    gdf['FLOOD_RISK'] = pd.cut(
        gdf['F_SHIM'],
        bins=[0, 0.5, 1.0, 2.0, float('inf')],
        labels=['낮음', '보통', '높음', '매우높음']
    )

    print(f"전처리 완료: {len(gdf)}행")
    return gdf



# ── 5. 공간조인으로 동별 집계 ──────────────────────────────
def aggregate_by_dong(gdf, boundary):
    # CRS 맞추기 - 5179로 수정
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:5179")
    gdf = gdf.to_crs("EPSG:4326")

    joined = gpd.sjoin(gdf, boundary[['EMD_CD', 'EMD_NM', 'geometry']], how='left', predicate='intersects')

    agg = joined.groupby('EMD_CD').agg(
        FLOOD_COUNT=('F_SHIM', 'count'),
        AVG_SHIM=('F_SHIM', 'mean'),
        MAX_SHIM=('F_SHIM', 'max'),
        AVG_AREA=('F_AREA', 'mean'),
        TOTAL_SCALE=('FLOOD_SCALE', 'sum'),
        AVG_DEPTH_PER_AREA=('FLOOD_DEPTH_PER_AREA', 'mean'),
        RECENT_YR=('F_YR', 'max'),
    ).reset_index()

    print(f"동별 집계 완료: {len(agg)}개 동")
    return agg


# ── 전체 실행 ───────────────────────────────────────────────
def run():
    print("\n[침수 흔적도 전처리 시작]")
    boundary = load_boundary()
    extract_dir = extract_flood()
    df = load_flood(extract_dir)
    gdf = process_flood(df)
    agg = aggregate_by_dong(gdf, boundary)

    # 상세 데이터 저장 (geometry 제외)
    detail = pd.DataFrame(gdf.drop(columns='geometry'))
    detail_path = os.path.join(PROCESSED_DIR, "flood_detail.csv")
    detail.to_csv(detail_path, index=False, encoding="utf-8-sig")
    print(f"상세 데이터 저장: {detail_path}")

    # 동별 집계 저장
    agg_path = os.path.join(PROCESSED_DIR, "flood_by_dong.csv")
    agg.to_csv(agg_path, index=False, encoding="utf-8-sig")
    print(f"동별 집계 저장: {agg_path}")

    print("\n[침수 흔적도 전처리 완료]")
    return gdf, agg


if __name__ == "__main__":
    run()