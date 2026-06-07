# preprocess/merge.py
import geopandas as gpd
import pandas as pd
import numpy as np
from zipfile import ZipFile
import os
import sys

from shapely import boundary

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import PROCESSED_DIR, BOUNDARY_DIR, BOUNDARY_FILE, RAINFALL_DIR, DEM_CSV

GRID_FILE = os.path.join(RAINFALL_DIR, "기상청41_단기예보 조회서비스_오픈API활용가이드_격자_위경도(2510).xlsx")
SHP_FILE = os.path.join(BOUNDARY_DIR, "boundary_extracted", "LSMD_ADM_SECT_UMD_11_202605.shp")


# ── 1. 서울 행정경계 로드 ──────────────────────────────────
def load_boundary():
    boundary = gpd.read_file(SHP_FILE, encoding="euc-kr")
    boundary = boundary.to_crs("EPSG:4326")
    print(f"행정경계 로드 완료: {len(boundary)}개 동")
    return boundary


# ── 2. DEM → 동 매핑 ──────────────────────────────────────
def map_dem_to_dong(boundary):
    dem_df = pd.read_csv(DEM_CSV, encoding="utf-8-sig")

    gdf = gpd.GeoDataFrame(
        dem_df,
        geometry=gpd.points_from_xy(dem_df['LON'], dem_df['LAT']),
        crs="EPSG:4326"
    )

    joined = gpd.sjoin(gdf, boundary[['EMD_CD', 'EMD_NM', 'geometry']], how='left', predicate='intersects')

    dem_by_dong = joined.groupby('EMD_CD').agg(
        AVG_ELEVATION=('ELEVATION', 'mean'),
        MIN_ELEVATION=('ELEVATION', 'min'),
        MAX_ELEVATION=('ELEVATION', 'max'),
    ).reset_index()

    print(f"DEM 동별 집계 완료: {len(dem_by_dong)}개 동")
    return dem_by_dong


# ── 3. 강우량 nx,ny → 위경도 변환 후 동 매핑 ──────────────
def map_rainfall_to_dong(boundary):
    grid_df = pd.read_excel(GRID_FILE)
    seoul_grid = grid_df[grid_df['1단계'] == '서울특별시'].copy()

    def dms_to_dd(deg, min_, sec):
        return deg + min_ / 60 + sec / 3600

    seoul_grid['LAT'] = seoul_grid.apply(
        lambda r: dms_to_dd(r['위도(시)'], r['위도(분)'], r['위도(초/100)'] / 100), axis=1
    )
    seoul_grid['LON'] = seoul_grid.apply(
        lambda r: dms_to_dd(r['경도(시)'], r['경도(분)'], r['경도(초/100)'] / 100), axis=1
    )

    gdf = gpd.GeoDataFrame(
        seoul_grid[['격자 X', '격자 Y', 'LAT', 'LON']],
        geometry=gpd.points_from_xy(seoul_grid['LON'], seoul_grid['LAT']),
        crs="EPSG:4326"
    )

    joined = gpd.sjoin(gdf, boundary[['EMD_CD', 'EMD_NM', 'geometry']], how='left', predicate='within')

    grid_mapping = joined[['격자 X', '격자 Y', 'EMD_CD']].dropna(subset=['EMD_CD'])
    mapping_path = os.path.join(PROCESSED_DIR, "grid_to_dong.csv")
    grid_mapping.to_csv(mapping_path, index=False, encoding="utf-8-sig")
    print(f"격자 → 동 매핑 저장: {mapping_path} ({len(grid_mapping)}행)")
    return grid_mapping


# ── 4. 하수관로 → 동 매핑 ─────────────────────────────────
def map_drainpipe_to_dong(boundary):
    master_path = os.path.join(PROCESSED_DIR, "location_master.csv")
    if not os.path.exists(master_path):
        print("location_master.csv 없음 - 하수관로 매핑 스킵")
        return None

    master = pd.read_csv(master_path, encoding="utf-8-sig")
    master = master.dropna(subset=['LAT', 'LON'])

    gdf = gpd.GeoDataFrame(
        master,
        geometry=gpd.points_from_xy(master['LON'], master['LAT']),
        crs="EPSG:4326"
    )

    joined = gpd.sjoin(gdf, boundary[['EMD_CD', 'EMD_NM', 'geometry']], how='left', predicate='within')

    pipe_mapping = joined[['UNQ_NO', 'EMD_CD', 'EMD_NM']].dropna(subset=['EMD_CD'])
    pipe_mapping_path = os.path.join(PROCESSED_DIR, "pipe_to_dong.csv")
    pipe_mapping.to_csv(pipe_mapping_path, index=False, encoding="utf-8-sig")
    print(f"하수관로 → 동 매핑 저장: {pipe_mapping_path} ({len(pipe_mapping)}행)")
    return pipe_mapping


# ── 5. 전체 머지 ───────────────────────────────────────────

def merge_all(boundary):
    flood_path = os.path.join(PROCESSED_DIR, "flood_by_dong.csv")
    flood_df = pd.read_csv(flood_path, encoding="utf-8-sig")
    flood_df['EMD_CD'] = flood_df['EMD_CD'].astype(str).str.zfill(8)

    dem_by_dong = map_dem_to_dong(boundary)
    dem_by_dong['EMD_CD'] = dem_by_dong['EMD_CD'].astype(str).str.zfill(8)

    # boundary에서 base 만들 때 EMD_CD 타입 명시
    base = pd.DataFrame({
        'EMD_CD': boundary['EMD_CD'].astype(str).str.zfill(8),
        'EMD_NM': boundary['EMD_NM']
    })

    print('base EMD_CD 샘플:', base['EMD_CD'].tolist()[:3])
    print('flood EMD_CD 샘플:', flood_df['EMD_CD'].tolist()[:3])
    print('dem EMD_CD 샘플:', dem_by_dong['EMD_CD'].tolist()[:3])

    result = base.merge(dem_by_dong, on='EMD_CD', how='left')
    result = result.merge(flood_df, on='EMD_CD', how='left')

    flood_cols = ['FLOOD_COUNT', 'AVG_SHIM', 'MAX_SHIM', 'AVG_AREA', 'TOTAL_SCALE', 'AVG_DEPTH_PER_AREA']
    for col in flood_cols:
        if col in result.columns:
            result[col] = result[col].fillna(0)

    output_path = os.path.join(PROCESSED_DIR, "merged_by_dong.csv")
    result.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"\n최종 머지 완료: {output_path} ({len(result)}행)")
    print(result[result['FLOOD_COUNT'] > 0].head())
    return result

# ── 전체 실행 ───────────────────────────────────────────────
def run():
    print("\n[데이터 머지 시작]")
    boundary = load_boundary()
    map_rainfall_to_dong(boundary)
    map_drainpipe_to_dong(boundary)
    merge_all(boundary)
    print("\n[데이터 머지 완료]")


if __name__ == "__main__":
    run()