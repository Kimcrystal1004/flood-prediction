# save as: model/make_tableau_master.py

import os
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 과거 시계열 데이터 원본
HISTORY_FILE = os.path.join(BASE_DIR, "data", "processed", "train_dataset_all_with_area.csv")
# 우리가 만든 최신 동별 요약 (예측 심각도 포함)
SEVERITY_FILE = os.path.join(BASE_DIR, "data", "final", "tableau_severity_map.csv")
# 최종 저장할 마스터 통합본 파일
OUTPUT_FILE = os.path.join(BASE_DIR, "data", "final", "tableau_master_dashboard.csv")

def main():
    print("[1] 과거 시계열 데이터 불러오기...")
    df_history = pd.read_csv(HISTORY_FILE)
    
    # 만약 원본 데이터에 '측정일시' 같은 날짜 컬럼이 YYYYMMDDHH 형식 등이라면
    # 태블로가 인식하기 쉽게 YYYY-MM-DD 형식으로 변환해 주면 좋습니다.
    # (여기서는 데이터 형태에 따라 날짜 컬럼명이 'YR_MTH', 'DATE', '측정일시' 등일 수 있으니 
    # 원본 파일에 맞춰 진행합니다. 일반적으로 그대로 둬도 태블로에서 파싱 가능합니다.)
    
    print("[2] 최신 동별 심각도 데이터 불러오기...")
    df_severity = pd.read_csv(SEVERITY_FILE)
    
    # 심각도 파일에서 필요한 알짜배기 컬럼만 선택
    # (이미 history에 있는 강수량/수위 등은 중복되므로 뺌)
    severity_cols = ['EMD_NM', 'PRED_SEVERITY', 'RISK_LEVEL', 'DONG_AREA_KM2']
    df_severity_subset = df_severity[severity_cols]
    
    print("[3] 두 데이터를 동 이름(EMD_NM) 기준으로 결합 중...")
    # 과거 데이터(history)의 각 행(동 이름) 옆에 최종 심각도를 쫙 붙여줍니다.
    df_master = pd.merge(df_history, df_severity_subset, on='EMD_NM', how='left')
    
    # 저장 경로 생성
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    
    # 저장
    df_master.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
    print(f"\n[완료] 대시보드 시각화용 통합 마스터 파일 생성 완료!")
    print(f"저장 위치: {OUTPUT_FILE}")
    print(f"총 행 수: {len(df_master):,}행")
    print("\n이제 태블로에서 'tableau_master_dashboard.csv' 하나만 불러서 모든 차트를 만드시면 됩니다!")

if __name__ == "__main__":
    main()