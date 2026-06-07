# =============================================================
# model/features.py
# 역할: train.py와 predict.py에서 공통으로 사용하는
#       피처 목록과 파생 피처 생성 함수를 한 곳에서 관리
# 사용법: from features import FEATURES, add_engineered_features
# =============================================================

# 모델에 입력되는 피처 전체 목록
# 이 목록을 train.py와 predict.py 양쪽이 공유해야 피처 불일치 오류가 없음
FEATURES = [
    "EMD_CD",                                           # 동 코드 (범주형)
    "AVG_ELEVATION", "MIN_ELEVATION", "MAX_ELEVATION",  # 지형 고도 (DEM)
    "FLOOD_COUNT", "AVG_SHIM", "MAX_SHIM",              # 과거 침수 이력
    "TOTAL_SCALE", "AVG_DEPTH_PER_AREA", "RECENT_YR",  # 과거 침수 규모
    "AVG_WATL", "MAX_WATL",                             # 하수관로 수위
    "AVG_RN1", "MAX_RN1", "TOTAL_RN1",                  # 강우량
    "RN1_INTENSITY", "WATL_SPIKE_RATE",                 # 파생: 집중도/급증률
    "LOW_ELEV_RISK", "MONTH",                           # 파생: 저지대 위험도, 계절
]

# 범주형으로 처리할 피처 (LightGBM이 자동 최적 분할)
CATEGORICAL_FEATURES = ["EMD_CD"]
