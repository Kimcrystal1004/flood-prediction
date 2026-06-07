# save as: preprocess/add_dong_area.py

import os
import glob
import pandas as pd
import shapefile
from shapely.geometry import shape

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOUNDARY_DIR = os.path.join(BASE_DIR, "data", "raw", "boundary")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")

OUT_AREA_FILE = os.path.join(PROCESSED_DIR, "dong_area.csv")
MERGED_FILE = os.path.join(PROCESSED_DIR, "merged_by_dong.csv")
PRED_FILE = os.path.join(PROCESSED_DIR, "prediction_input.csv")
TRAIN_ALL_FILE = os.path.join(PROCESSED_DIR, "train_dataset_all.csv")

OUT_MERGED_FILE = os.path.join(PROCESSED_DIR, "merged_by_dong_with_area.csv")
OUT_PRED_FILE = os.path.join(PROCESSED_DIR, "prediction_input_with_area.csv")
OUT_TRAIN_ALL_FILE = os.path.join(PROCESSED_DIR, "train_dataset_all_with_area.csv")

def find_shp_file(boundary_dir):
    shp_list = glob.glob(os.path.join(boundary_dir, "*.shp"))
    if not shp_list:
        raise FileNotFoundError(f"shp 파일을 찾을 수 없습니다: {boundary_dir}")
    return shp_list[0]

def extract_area_pyshp():
    shp_file = find_shp_file(BOUNDARY_DIR)
    print(f"[1] 행정경계 shp 읽기 (가벼운 모드): {shp_file}")
    
    sf = shapefile.Reader(shp_file, encoding='cp949')
    records = sf.records()
    shapes = sf.shapes()
    
    # 컬럼 찾기
    fields = [f[0] for f in sf.fields[1:]]
    code_candidates = ["EMD_CD", "EMD_CODE", "A1", "ADM_CD", "ADM_DR_CD", "법정동코드", "ADM_CD2"]
    name_candidates = ["EMD_NM", "EMD_KOR_NM", "ADM_NM", "KOR_NM", "법정동명", "ADM_DR_NM"]
    
    code_idx = next((i for i, f in enumerate(fields) if f in code_candidates), None)
    name_idx = next((i for i, f in enumerate(fields) if f in name_candidates), None)
    
    data = []
    print("[2] 면적 계산 중...")
    for rec, shp in zip(records, shapes):
        if shp.shapeType == shapefile.NULL:
            continue
            
        code = str(rec[code_idx])
        name = str(rec[name_idx])
        
        # 순수 파이썬 좌표 변환 후 Shapely로 면적 계산
        geom = shape(shp.__geo_interface__)
        area_m2 = geom.area
        
        data.append({"EMD_CD": code, "EMD_NM": name, "DONG_AREA_M2": area_m2})
        
    area_df = pd.DataFrame(data)
    area_df = area_df.groupby(["EMD_CD", "EMD_NM"], as_index=False)["DONG_AREA_M2"].sum()
    area_df["DONG_AREA_KM2"] = area_df["DONG_AREA_M2"] / 1_000_000
    
    area_df.to_csv(OUT_AREA_FILE, index=False, encoding="utf-8-sig")
    print(f"[3] 저장 완료: {OUT_AREA_FILE} ({len(area_df)}행)")
    
    return area_df

def attach_area(df, name, area_df):
    df = df.copy()
    df["EMD_CD"] = df["EMD_CD"].astype(str)
    
    merged = df.merge(area_df[["EMD_CD", "DONG_AREA_M2", "DONG_AREA_KM2"]], on="EMD_CD", how="left")
    
    if "AVG_AREA" in merged.columns:
        merged["AVG_AREA_RATIO"] = merged["AVG_AREA"] / merged["DONG_AREA_M2"]
    
    if "AVG_AREA_RATIO" in merged.columns and "AVG_SHIM" in merged.columns:
        merged["SEVERITY_INDEX"] = merged["AVG_AREA_RATIO"] * merged["AVG_SHIM"]
        
    matched = merged["DONG_AREA_M2"].notna().sum()
    print(f"[병합] {name}: {matched:,}/{len(merged):,} 행 면적 매칭 완료")
    
    return merged

def main():
    area_df = extract_area_pyshp()
    
    if os.path.exists(MERGED_FILE):
        df = pd.read_csv(MERGED_FILE, dtype={"EMD_CD": str})
        attach_area(df, "merged_by_dong.csv", area_df).to_csv(OUT_MERGED_FILE, index=False, encoding="utf-8-sig")
        
    if os.path.exists(PRED_FILE):
        df = pd.read_csv(PRED_FILE, dtype={"EMD_CD": str})
        attach_area(df, "prediction_input.csv", area_df).to_csv(OUT_PRED_FILE, index=False, encoding="utf-8-sig")
        
    if os.path.exists(TRAIN_ALL_FILE):
        df = pd.read_csv(TRAIN_ALL_FILE, dtype={"EMD_CD": str})
        attach_area(df, "train_dataset_all.csv", area_df).to_csv(OUT_TRAIN_ALL_FILE, index=False, encoding="utf-8-sig")
        
    print("\n[완료] 동별 면적 추출 완료!")

if __name__ == "__main__":
    main()