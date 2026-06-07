# preprocess/realtime_merge.py
import pandas as pd
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import PROCESSED_DIR, DRAINPIPE_DIR, RAINFALL_DIR


# ── 1. 하수관로 동별 집계 ──────────────────────────────────
def aggregate_drainpipe():
    filepath = os.path.join(DRAINPIPE_DIR, "drainpipe_realtime.csv")
    if not os.path.exists(filepath):
        print("drainpipe_realtime.csv 없음 - 하수관로 스킵")
        return None

    df = pd.read_csv(filepath, encoding="utf-8-sig")
    df['MSRMT_WATL'] = pd.to_numeric(df['MSRMT_WATL'], errors='coerce')
    df['MSRMT_YMD'] = pd.to_datetime(df['MSRMT_YMD'])

    # 가장 최신 시점 데이터만 사용
    latest_time = df['MSRMT_YMD'].max()
    df = df[df['MSRMT_YMD'] == latest_time].copy()
    print(f"하수관로 기준 시각: {latest_time}")

    # pipe_to_dong 매핑
    pipe_to_dong = pd.read_csv(
        os.path.join(PROCESSED_DIR, "pipe_to_dong.csv"),
        encoding="utf-8-sig"
    )
    pipe_to_dong['EMD_CD'] = pipe_to_dong['EMD_CD'].astype(str).str.zfill(8)

    df = df.merge(pipe_to_dong[['UNQ_NO', 'EMD_CD']], on='UNQ_NO', how='left')

    # 동별 집계
    agg = df.groupby('EMD_CD').agg(
        AVG_WATL=('MSRMT_WATL', 'mean'),
        MAX_WATL=('MSRMT_WATL', 'max'),
        SENSOR_COUNT=('UNQ_NO', 'count'),
    ).reset_index()

    print(f"하수관로 동별 집계 완료: {len(agg)}개 동")
    return agg


# ── 2. 강우량 동별 집계 ────────────────────────────────────
def aggregate_rainfall():
    filepath = os.path.join(RAINFALL_DIR, "rainfall_realtime.csv")
    if not os.path.exists(filepath):
        print("rainfall_realtime.csv 없음 - 강우량 스킵")
        return None

    df = pd.read_csv(filepath, encoding="utf-8-sig")
    df['RN1'] = pd.to_numeric(df['RN1'], errors='coerce').fillna(0)

    # grid_to_dong 매핑
    grid_to_dong = pd.read_csv(
        os.path.join(PROCESSED_DIR, "grid_to_dong.csv"),
        encoding="utf-8-sig"
    )
    grid_to_dong['EMD_CD'] = grid_to_dong['EMD_CD'].astype(str).str.zfill(8)
    grid_to_dong = grid_to_dong.rename(columns={'격자 X': 'NX', '격자 Y': 'NY'})

    df = df.merge(grid_to_dong[['NX', 'NY', 'EMD_CD']], on=['NX', 'NY'], how='left')

    # 동별 집계
    agg = df.groupby('EMD_CD').agg(
        AVG_RN1=('RN1', 'mean'),
        MAX_RN1=('RN1', 'max'),
        TOTAL_RN1=('RN1', 'sum'),
    ).reset_index()

    print(f"강우량 동별 집계 완료: {len(agg)}개 동")
    return agg


# ── 3. 전체 병합 ───────────────────────────────────────────
def merge_realtime():
    print("\n[실시간 데이터 병합 시작]")

    # 정적 베이스 로드
    base = pd.read_csv(
        os.path.join(PROCESSED_DIR, "merged_by_dong.csv"),
        encoding="utf-8-sig"
    )
    base['EMD_CD'] = base['EMD_CD'].astype(str).str.zfill(8)

    # 하수관로 집계
    drainpipe_agg = aggregate_drainpipe()
    if drainpipe_agg is not None:
        drainpipe_agg['EMD_CD'] = drainpipe_agg['EMD_CD'].astype(str).str.zfill(8)
        base = base.merge(drainpipe_agg, on='EMD_CD', how='left')
        base['AVG_WATL'] = base['AVG_WATL'].fillna(0)
        base['MAX_WATL'] = base['MAX_WATL'].fillna(0)
        base['SENSOR_COUNT'] = base['SENSOR_COUNT'].fillna(0)

    # 강우량 집계
    rainfall_agg = aggregate_rainfall()
    if rainfall_agg is not None:
        rainfall_agg['EMD_CD'] = rainfall_agg['EMD_CD'].astype(str).str.zfill(8)
        base = base.merge(rainfall_agg, on='EMD_CD', how='left')
        base['AVG_RN1'] = base['AVG_RN1'].fillna(0)
        base['MAX_RN1'] = base['MAX_RN1'].fillna(0)
        base['TOTAL_RN1'] = base['TOTAL_RN1'].fillna(0)

    # 저장
    output_path = os.path.join(PROCESSED_DIR, "prediction_input.csv")
    base.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"\n저장 완료: {output_path} ({len(base)}행)")
    print(base.head())
    return base


if __name__ == "__main__":
    merge_realtime()