# model/train_severity.py
# ─────────────────────────────────────────────────────────────
# 목적: 과거 5년치 데이터로 LightGBM 학습
#       "현재 상황 입력 → 3시간 뒤 침수 심각도(SEVERITY_INDEX) 예측"
# ─────────────────────────────────────────────────────────────
import os
import sys
import pandas as pd
import numpy as np
import pickle
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error

BASE_DIR       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRAIN_FILE     = os.path.join(BASE_DIR, "data", "processed", "train_dataset_all_with_area.csv")
MODEL_SAVE_PATH = os.path.join(BASE_DIR, "model", "saved", "severity_lgbm_model.pkl")

# ── 실제 데이터에 존재하는 컬럼명 그대로 사용 ─────────────────
FEATURES = [
    'AVG_ELEVATION', 'MIN_ELEVATION', 'MAX_ELEVATION',
    'FLOOD_COUNT',
    'AVG_SHIM', 'MAX_SHIM', 'AVG_AREA',
    'TOTAL_SCALE', 'AVG_DEPTH_PER_AREA',
    'RECENT_YR',
    'DONG_AREA',           # add_dong_area.py 실행 후 생성되는 컬럼
    'AVG_WATL', 'MAX_WATL',
    'AVG_RN1',  'MAX_RN1', 'TOTAL_RN1',
    'YEAR',
]

# ── SEVERITY_INDEX 계산 (0~100점) ──────────────────────────────
# 침수심(35%) + 침수면적(25%) + 총규모(25%) + 발생횟수(15%) 가중합
def compute_severity_index(df: pd.DataFrame) -> pd.Series:
    cols_weights = [
        ('AVG_SHIM',   0.35),
        ('AVG_AREA',   0.25),
        ('TOTAL_SCALE',0.25),
        ('FLOOD_COUNT',0.15),
    ]
    normed = pd.DataFrame(index=df.index)
    for col, _ in cols_weights:
        min_v, max_v = df[col].min(), df[col].max()
        normed[col] = (df[col] - min_v) / (max_v - min_v) if max_v > min_v else 0.0
    score = sum(normed[col] * w for col, w in cols_weights)
    return (score * 100).round(2)


def main():
    print("\n[침수 위험도 모델 학습] — 3시간 뒤 SEVERITY_INDEX 예측 버전")

    # 1. 데이터 로드
    print(f"  데이터 로드: {TRAIN_FILE}")
    df = pd.read_csv(TRAIN_FILE, encoding='utf-8-sig')
    df['DATETIME'] = pd.to_datetime(df['DATETIME'])
    print(f"  총 행 수: {len(df):,}")

    # 2. 결측치 처리
    df[FEATURES] = df[FEATURES].fillna(0)

    # 3. SEVERITY_INDEX 계산 (현재 시점 기준)
    df['SEVERITY_INDEX'] = compute_severity_index(df)

    # 4. 핵심: Target을 3시간 뒤로 이동 (shift -1)
    #    동(EMD_CD)별로 정렬 후, 다음 시점의 SEVERITY_INDEX를 정답으로 사용
    #    → "지금 이 상황이면 3시간 뒤 위험도는?"을 AI가 학습
    print("  Target을 3시간 뒤 시점으로 이동 중 (shift -1)...")
    df = df.sort_values(['EMD_CD', 'DATETIME']).reset_index(drop=True)
    df['TARGET'] = df.groupby('EMD_CD')['SEVERITY_INDEX'].shift(-1)
    df = df.dropna(subset=['TARGET']).reset_index(drop=True)
    print(f"  학습 가능 행 수 (shift 후): {len(df):,}")

    # 5. Feature / Target 분리
    missing = [f for f in FEATURES if f not in df.columns]
    if missing:
        print(f"\n  ⚠️  누락된 Feature 컬럼: {missing}")
        print("     preprocess/add_dong_area.py 를 먼저 실행했는지 확인하세요.")
        return

    X = df[FEATURES]
    y = df['TARGET']

    # 6. 학습 / 검증 분리 (8:2)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    print(f"  학습셋: {len(X_train):,}행 / 검증셋: {len(X_test):,}행")

    # 7. LightGBM 모델 학습
    print("  LightGBM 학습 중...")
    model = lgb.LGBMRegressor(
        n_estimators=500,
        learning_rate=0.05,
        max_depth=7,
        num_leaves=63,
        min_child_samples=20,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.1,
        reg_lambda=0.1,
        random_state=42,
        n_jobs=-1,
        verbose=-1,
    )
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        eval_metric='rmse',
        callbacks=[lgb.early_stopping(stopping_rounds=50, verbose=False)],
    )

    # 8. 성능 평가
    y_pred = model.predict(X_test)
    y_pred = [max(0, p) for p in y_pred]   # 음수 보정
    rmse = root_mean_squared_error(y_test, y_pred)
    mae  = mean_absolute_error(y_test, y_pred)
    r2   = r2_score(y_test, y_pred)
    print(f"\n  ✅ 검증 성능")
    print(f"     RMSE (평균 오차): {rmse:.4f}점")
    print(f"     MAE  (평균 오차): {mae:.4f}점")
    print(f"     R²   (설명력)  : {r2:.4f}")

    # 9. Feature 중요도 Top 10 출력
    importance = pd.Series(model.feature_importances_, index=FEATURES)
    importance = importance.sort_values(ascending=False)
    print("\n  📊 Feature 중요도 Top 10:")
    for feat, imp in importance.head(10).items():
        bar = "█" * int(imp / importance.max() * 20)
        print(f"     {feat:<25} {bar} ({imp:.0f})")

    # 10. 모델 저장
    os.makedirs(os.path.dirname(MODEL_SAVE_PATH), exist_ok=True)
    with open(MODEL_SAVE_PATH, 'wb') as f:
        pickle.dump(model, f)
    print(f"\n  💾 모델 저장 완료: {MODEL_SAVE_PATH}")
    print("  → 이 모델은 '현재 상황 입력 → 3시간 뒤 SEVERITY_INDEX 출력' 방식으로 예측합니다.")


if __name__ == "__main__":
    main()
