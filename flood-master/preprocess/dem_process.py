# preprocess/dem_process.py
import rasterio
from rasterio.merge import merge
from rasterio.mask import mask
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.transform import xy
import geopandas as gpd
import numpy as np
import pandas as pd
from zipfile import ZipFile
import os
import sys
from zipfile import ZipFile
import tempfile

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DEM_DIR, DEM_FILES, DEM_IMG_NAMES, BOUNDARY_FILE, PROCESSED_DIR


# ── 1. zip에서 img 추출 ─────────────────────────────────────
def extract_dem():
    for zip_path, img_name in zip(DEM_FILES, DEM_IMG_NAMES):
        extract_path = os.path.join(DEM_DIR, img_name)
        if os.path.exists(extract_path):
            print(f"이미 추출됨: {img_name}")
            continue
        with ZipFile(zip_path) as z:
            z.extract(img_name, DEM_DIR)
        print(f"추출 완료: {img_name}")


# ── 2. 두 타일 모자이크 ─────────────────────────────────────
def merge_tiles():
    merged_path = os.path.join(DEM_DIR, "dem_merged.tif")
    if os.path.exists(merged_path):
        print("모자이크 파일 이미 존재 - 스킵")
        return merged_path

    tile_paths = [os.path.join(DEM_DIR, name) for name in DEM_IMG_NAMES]
    tiles = [rasterio.open(p) for p in tile_paths]

    mosaic, transform = merge(tiles)

    meta = tiles[0].meta.copy()
    meta.update({
        "driver": "GTiff",
        "height": mosaic.shape[1],
        "width": mosaic.shape[2],
        "transform": transform
    })

    with rasterio.open(merged_path, "w", **meta) as dest:
        dest.write(mosaic)

    for t in tiles:
        t.close()

    print("모자이크 완료")
    return merged_path


# ── 3. 서울시 경계로 클리핑 ─────────────────────────────────
def clip_to_seoul(merged_path):
    clipped_path = os.path.join(DEM_DIR, "dem_seoul_5179.tif")
    if os.path.exists(clipped_path):
        print("클리핑 파일 이미 존재 - 스킵")
        return clipped_path

    # zip 압축 해제 후 읽기
    boundary_extract_dir = os.path.join(os.path.dirname(BOUNDARY_FILE), "boundary_extracted")
    if not os.path.exists(boundary_extract_dir):
        with ZipFile(BOUNDARY_FILE) as z:
            z.extractall(boundary_extract_dir)
        print("경계 파일 압축 해제 완료")

    # shp 파일 찾기
    shp_file = None
    for f in os.listdir(boundary_extract_dir):
        if f.endswith(".shp"):
            shp_file = os.path.join(boundary_extract_dir, f)
            break

    if shp_file is None:
        raise FileNotFoundError("shp 파일을 찾을 수 없어요")

    seoul = gpd.read_file(shp_file)
    print(f"경계 파일 CRS: {seoul.crs}")

    with rasterio.open(merged_path) as src:
        seoul = seoul.to_crs(src.crs)
        clipped, clip_transform = mask(src, seoul.geometry, crop=True, nodata=-9999)
        clip_meta = src.meta.copy()
        clip_meta.update({
            "height": clipped.shape[1],
            "width": clipped.shape[2],
            "transform": clip_transform,
            "nodata": -9999
        })

    with rasterio.open(clipped_path, "w", **clip_meta) as dest:
        dest.write(clipped)

    print("서울 클리핑 완료")
    return clipped_path


# ── 4. EPSG:5179 → EPSG:4326 변환 ──────────────────────────
def reproject_to_wgs84(clipped_path):
    reprojected_path = os.path.join(DEM_DIR, "dem_seoul_4326.tif")
    if os.path.exists(reprojected_path):
        print("좌표변환 파일 이미 존재 - 스킵")
        return reprojected_path

    with rasterio.open(clipped_path) as src:
        transform_4326, width, height = calculate_default_transform(
            src.crs, "EPSG:4326", src.width, src.height, *src.bounds
        )
        meta_4326 = src.meta.copy()
        meta_4326.update({
            "crs": "EPSG:4326",
            "transform": transform_4326,
            "width": width,
            "height": height,
            "nodata": -9999
        })

        with rasterio.open(reprojected_path, "w", **meta_4326) as dst:
            reproject(
                source=rasterio.band(src, 1),
                destination=rasterio.band(dst, 1),
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=transform_4326,
                dst_crs="EPSG:4326",
                resampling=Resampling.bilinear,
                src_nodata=-9999,
                dst_nodata=-9999
            )

    print("좌표 변환 완료 (5179 → 4326)")
    return reprojected_path


# ── 5. 래스터 → CSV 변환 ────────────────────────────────────
def to_csv(reprojected_path):
    with rasterio.open(reprojected_path) as src:
        data = src.read(1)
        transform = src.transform

    rows, cols = np.where(data != -9999)
    values = data[rows, cols]
    
    # xy 함수는 (row, col) 순서로 받아서 (x=경도, y=위도) 반환
    xs, ys = xy(transform, rows, cols)

    dem_df = pd.DataFrame({
        "LAT": ys,   # y = 위도
        "LON": xs,   # x = 경도
        "ELEVATION": values
    })

    output_path = os.path.join(PROCESSED_DIR, "dem_seoul.csv")
    dem_df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"CSV 변환 완료: {output_path} ({len(dem_df)}행)")
    return dem_df


# ── 전체 실행 ───────────────────────────────────────────────
def run():
    print("\n[DEM 전처리 시작]")
    extract_dem()
    merged_path = merge_tiles()
    clipped_path = clip_to_seoul(merged_path)
    reprojected_path = reproject_to_wgs84(clipped_path)
    to_csv(reprojected_path)
    print("\n[DEM 전처리 완료]")


if __name__ == "__main__":
    run()