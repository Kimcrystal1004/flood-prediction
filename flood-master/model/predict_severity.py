# model/predict_severity.py
import os
import pickle
import pandas as pd
from datetime import datetime, timedelta


BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_FILE  = os.path.join(BASE_DIR, "data", "processed", "prediction_input.csv")
MODEL_PATH  = os.path.join(BASE_DIR, "model", "saved", "severity_lgbm_model.pkl")
OUTPUT_FILE = os.path.join(BASE_DIR, "data", "processed", "risk_output.csv")


FEATURES = [
    'AVG_ELEVATION', 'MIN_ELEVATION', 'MAX_ELEVATION',
    'FLOOD_COUNT',
    'AVG_SHIM', 'AVG_AREA',
    'DONG_AREA_M2', 'AVG_AREA_RATIO',
    'AVG_WATL', 'MAX_WATL',
    'AVG_RN1', 'MAX_RN1', 'TOTAL_RN1',
]


def predict():
    print("\n[침수 위험도 예측 — 3시간 뒤 SEVERITY_INDEX]")

    # 1. 입력 데이터 로드
    if not os.path.exists(INPUT_FILE):
        print(f"  ⚠️  입력 파일 없음: {INPUT_FILE}")
        return

    df = pd.read_csv(INPUT_FILE, encoding='utf-8-sig')

    # 없는 컬럼은 0으로 자동 보완
    if 'DONG_AREA' not in df.columns:
        df['DONG_AREA'] = 0
    if 'YEAR' not in df.columns:
        df['YEAR'] = datetime.now().year

    for col in FEATURES:
        if col not in df.columns:
            df[col] = 0

    df[FEATURES] = df[FEATURES].fillna(0)

    # 2. 모델 로드
    if not os.path.exists(MODEL_PATH):
        print(f"  ⚠️  모델 파일 없음: {MODEL_PATH}")
        print("     train_severity.py 를 먼저 실행하세요.")
        return

    with open(MODEL_PATH, 'rb') as f:
        model = pickle.load(f)

    # 3. 예측 — 모델이 학습한 피처만 선택 (없는 컬럼은 0으로 채움)
    X = df[FEATURES]
    try:
        trained_features = list(model.feature_names_in_)
        # 없는 컬럼은 0으로 보완
        for col in trained_features:
            if col not in df.columns:
                df[col] = 0
        X = df[trained_features]
        print(f"  ✅ 모델 피처 {len(trained_features)}개 사용: {trained_features}")
    except AttributeError:
        print(f"  ✅ FEATURES 목록 {len(FEATURES)}개 사용")

    preds = model.predict(X)

    # 4. 예측 시각 (현재 + 3시간)
    now       = datetime.now()
    pred_time = (now + timedelta(hours=3)).strftime('%Y-%m-%d %H:%M')

    # 5. 결과 저장
    def classify(score):
        if score >= 70:   return '위험'
        elif score >= 40: return '주의'
        elif score >= 10: return '관심'
        else:             return '안전'

    result = df[['EMD_CD', 'EMD_NM']].copy()
    result['PRED_DATETIME']  = pred_time
    result['COLLECTED_AT']   = now.strftime('%Y-%m-%d %H:%M')
    result['PRED_SEVERITY']  = preds
    result['RISK_LEVEL']     = result['PRED_SEVERITY'].apply(classify)

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    result.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')

    print(f"  💾 예측 완료 → {OUTPUT_FILE}")
    print(f"  예측 대상 시각: {pred_time} (현재로부터 3시간 뒤)")
    print(f"  예측 동 수: {len(result)}개")
    print(f"\n  위험 등급 분포:")
    print(result['RISK_LEVEL'].value_counts().to_string())
    return result


if __name__ == "__main__":
    predict()