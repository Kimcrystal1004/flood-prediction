# model/make_tableau_master.py
import os
import pandas as pd
from datetime import datetime


BASE_DIR      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RISK_FILE     = os.path.join(BASE_DIR, "data", "processed", "risk_output.csv")
INPUT_FILE    = os.path.join(BASE_DIR, "data", "processed", "prediction_input.csv")
TRAIN_FILE    = os.path.join(BASE_DIR, "data", "processed", "train_dataset_all.csv")
MASTER_OUT    = os.path.join(BASE_DIR, "data", "final", "tableau_master_dashboard.csv")
TIMELINE_OUT  = os.path.join(BASE_DIR, "data", "final", "tableau_timeline.csv")


def make_tableau():
    print("\n[태블로 마스터 대시보드 데이터 생성]")
    os.makedirs(os.path.join(BASE_DIR, "data", "final"), exist_ok=True)

    # ── 1. 예측 결과 로드 ─────────────────────────────────
    if not os.path.exists(RISK_FILE):
        print(f"  ⚠️  예측 결과 파일 없음: {RISK_FILE}")
        return
    risk = pd.read_csv(RISK_FILE, encoding='utf-8-sig')

    if 'PRED_DATETIME' not in risk.columns:
        risk['PRED_DATETIME'] = datetime.now().strftime('%Y-%m-%d %H:%M')
    if 'PRED_SEVERITY' not in risk.columns:
        risk['PRED_SEVERITY'] = 0
    if 'RISK_LEVEL' not in risk.columns:
        risk['RISK_LEVEL'] = '안전'

    # ── 2. 실시간 입력 데이터 로드 ────────────────────────
    if not os.path.exists(INPUT_FILE):
        print(f"  ⚠️  입력 데이터 파일 없음: {INPUT_FILE}")
        return
    inp = pd.read_csv(INPUT_FILE, encoding='utf-8-sig')

    # ── 3. 마스터 병합 저장 ───────────────────────────────
    master = pd.merge(risk, inp, on=['EMD_CD', 'EMD_NM'], how='left')
    master['UPDATE_TIME'] = datetime.now().strftime('%Y-%m-%d %H:%M')
    level_map = {'안전': 1, '관심': 2, '주의': 3, '위험': 4}
    master['RISK_LEVEL_NUM'] = master['RISK_LEVEL'].map(level_map).fillna(1).astype(int)

    master.to_csv(MASTER_OUT, index=False, encoding='utf-8-sig')
    print(f"  💾 마스터 저장 완료: {MASTER_OUT}  ({len(master)}행)")

    # ── 4. 월별 시계열 + 현재 예측값 합쳐서 timeline 저장 ─
    if not os.path.exists(TRAIN_FILE):
        print(f"  ⚠️  학습 데이터 없음, timeline 생략: {TRAIN_FILE}")
    else:
        train = pd.read_csv(TRAIN_FILE, encoding='utf-8-sig')
        train["DATETIME"] = pd.to_datetime(train["DATETIME"])
        train["연월"] = train["DATETIME"].dt.to_period("M").astype(str)
        dong_count = train["EMD_CD"].nunique()

        # 과거 데이터 월별 집계
        hist = train.groupby("연월").agg(
            평균강수량=("AVG_RN1",    "mean"),
            최대강수량=("MAX_RN1",    "max"),
            침수발생건수=("FLOOD_COUNT", "sum"),
            평균수위=("AVG_WATL",   "mean"),
            평균심도=("AVG_SHIM",   "mean"),
        ).reset_index()
        hist["침수발생건수"] = (hist["침수발생건수"] / dong_count).round(2)
        hist["구분"] = "과거"

        # 현재 예측값 1행 추가
        now_ym = datetime.now().strftime("%Y-%m")
        pred_row = pd.DataFrame([{
            "연월":        now_ym,
            "평균강수량":   master["AVG_RN1"].mean(),
            "최대강수량":   master["MAX_RN1"].max(),
            "침수발생건수": master["PRED_SEVERITY"].mean(),  # 예측 위험도를 대표값으로
            "평균수위":    master["AVG_WATL"].mean(),
            "평균심도":    master["AVG_SHIM"].mean() if "AVG_SHIM" in master.columns else 0,
            "구분":        "예측",
        }])

        timeline = pd.concat([hist, pred_row], ignore_index=True)
        timeline.to_csv(TIMELINE_OUT, index=False, encoding='utf-8-sig')
        print(f"  💾 타임라인 저장 완료: {TIMELINE_OUT}  ({len(timeline)}행, "
            f"{timeline['연월'].min()} ~ {timeline['연월'].max()})")

    pred_time = risk['PRED_DATETIME'].iloc[0]
    print(f"\n  📊 위험 등급 분포 (예측 기준 시각: {pred_time})")
    print(master['RISK_LEVEL'].value_counts().to_string())
    return master


if __name__ == "__main__":
    make_tableau()