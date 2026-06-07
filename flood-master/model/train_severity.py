import os
import pandas as pd
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score, root_mean_squared_error
import pickle

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRAIN_FILE = os.path.join(BASE_DIR, "data", "processed", "train_dataset_all_with_area.csv")
MODEL_SAVE_PATH = os.path.join(BASE_DIR, "model", "saved", "severity_lgbm_model.pkl")

# 학습에 사용할 특성(피처) 정의
FEATURES = [
    'AVG_ELEVATION', 'MIN_ELEVATION', 'MAX_ELEVATION',
    'FLOOD_COUNT', 'AVG_SHIM', 'AVG_AREA', 
    'DONG_AREA_M2', 'AVG_AREA_RATIO', # 새롭게 추가된 면적 정보
    'AVG_WATL', 'MAX_WATL', 
    'AVG_RN1', 'MAX_RN1', 'TOTAL_RN1'
]

TARGET = 'SEVERITY_INDEX'

def main():
    print(f"[1] 데이터 불러오기: {TRAIN_FILE}")
    df = pd.read_csv(TRAIN_FILE)
    
    # 결측치 처리 (면적이 없거나 비어있는 경우 0으로 대체)
    df[FEATURES] = df[FEATURES].fillna(0)
    df[TARGET] = df[TARGET].fillna(0)
    
    # 심각도 분포가 0에 몰려있을 수 있으므로 0 이상인 데이터에 약간의 가중치 부여
    X = df[FEATURES]
    y = df[TARGET]
    
    # 시간 순서에 따른 분할 (랜덤보다는 뒷부분 데이터를 테스트로 사용)
    # 여기서는 빠른 테스트를 위해 일반 분할 사용 (8:2)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    print("[2] LightGBM 회귀 모델 학습 시작...")
    # 회귀(Regression) 모델 세팅
    model = lgb.LGBMRegressor(
        n_estimators=500,
        learning_rate=0.05,
        max_depth=7,
        random_state=42,
        n_jobs=-1
    )
    
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        eval_metric='rmse',
        callbacks=[lgb.early_stopping(stopping_rounds=50, verbose=False)]
    )
    
    print("[3] 모델 평가")
    y_pred = model.predict(X_test)
    
    # 0 이하로 예측된 값은 0으로 보정 (심각도는 음수가 될 수 없으므로)
    y_pred = [max(0, p) for p in y_pred] 
    
    rmse = root_mean_squared_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    
    print(f" - RMSE (평균 오차): {rmse:.4f}")
    print(f" - R2 Score: {r2:.4f}")
    
    # 모델 저장 폴더가 없으면 생성
    os.makedirs(os.path.dirname(MODEL_SAVE_PATH), exist_ok=True)
    
    with open(MODEL_SAVE_PATH, 'wb') as f:
        pickle.dump(model, f)
    
    print(f"[4] 학습된 모델 저장 완료: {MODEL_SAVE_PATH}")
    
    # (선택) 중요도 파악을 위한 피처 중요도 출력
    importance = pd.DataFrame({
        'feature': FEATURES,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    print("\n[상위 5개 중요 피처]")
    print(importance.head(5))

if __name__ == "__main__":
    main()