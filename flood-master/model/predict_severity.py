# save as: model/predict_severity.py

import os
import pandas as pd
import pickle

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, "model", "saved", "severity_lgbm_model.pkl")
INPUT_FILE = os.path.join(BASE_DIR, "data", "processed", "prediction_input_with_area.csv")
OUTPUT_FILE = os.path.join(BASE_DIR, "data", "final", "tableau_severity_map.csv")

FEATURES = [
    'AVG_ELEVATION', 'MIN_ELEVATION', 'MAX_ELEVATION',
    'FLOOD_COUNT', 'AVG_SHIM', 'AVG_AREA', 
    'DONG_AREA_M2', 'AVG_AREA_RATIO', 
    'AVG_WATL', 'MAX_WATL', 
    'AVG_RN1', 'MAX_RN1', 'TOTAL_RN1'
]

def main():
    print(f"[1] 모델 불러오기: {MODEL_PATH}")
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError("학습된 모델 파일이 없습니다. train_severity.py를 먼저 실행하세요.")
        
    with open(MODEL_PATH, 'rb') as f:
        model = pickle.load(f)
        
    print(f"[2] 예측용 입력 데이터 불러오기: {INPUT_FILE}")
    df = pd.read_csv(INPUT_FILE)
    
    # 결측치 처리 (훈련 때와 동일하게)
    df[FEATURES] = df[FEATURES].fillna(0)
    
    print("[3] 각 동별 침수 심각도 예측 중...")
    predictions = model.predict(df[FEATURES])
    
    # 예측값 보정 (음수 방지 및 소수점 4자리까지 반올림)
    df['PRED_SEVERITY'] = [round(max(0, p), 4) for p in predictions]
    
    # --- 태블로 시각화를 위한 등급(위험도 단계) 추가 ---
    # 심각도 분포에 따라 안전/주의/경계/심각 으로 나눕니다.
    # (기준값은 데이터에 따라 추후 태블로에서 조정해도 됩니다)
    def assign_risk_level(score):
        if score == 0:
            return '안전'
        elif score < 0.005:  # 상대적으로 낮은 수치
            return '주의'
        elif score < 0.02:
            return '경계'
        else:
            return '심각'
            
    df['RISK_LEVEL'] = df['PRED_SEVERITY'].apply(assign_risk_level)
    
    # 저장할 결과 데이터만 추리기 (태블로 맵용)
    result_columns = [
        'EMD_CD', 'EMD_NM',          # 법정동 코드/이름 (지도 매칭용)
        'PRED_SEVERITY',             # 연속형 심각도 점수 (그라데이션 색상용)
        'RISK_LEVEL',                # 범주형 위험 단계 (라벨링용)
        'AVG_RN1', 'TOTAL_RN1',      # 당시 강수량 정보 (툴팁용)
        'AVG_WATL',                  # 당시 수위 정보 (툴팁용)
        'AVG_ELEVATION',             # 평균 고도 (툴팁용)
        'DONG_AREA_KM2'              # 동 면적
    ]
    
    final_df = df[result_columns]
    
    # 최종 결과물 저장 경로 생성
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    
    final_df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
    
    print(f"\n[완료] 태블로 시각화용 최종 데이터 저장 성공: {OUTPUT_FILE}")
    print("\n[태블로 연결 가이드]")
    print("1. 태블로에서 텍스트 파일(CSV)로 'tableau_severity_map.csv'를 연결하세요.")
    print("2. 'EMD_NM(또는 EMD_CD)' 컬럼의 지리적 역할을 '시군구' 또는 '사용자 지정'으로 설정하세요.")
    print("3. EMD_NM을 더블클릭하여 맵을 띄운 뒤, [PRED_SEVERITY]를 '색상' 마크에 올리면 완벽한 심각도 지도가 완성됩니다!")

if __name__ == "__main__":
    main()