# 🌊 서울시 침수 위험도 예측 프로젝트

## 프로젝트 개요
서울시 하수관로 수위, 강우량, DEM(수치표고모델), 침수 흔적도 데이터를 활용하여 동 단위 실시간 침수 위험도를 예측하고, 이를 태블로 대시보드로 시각화하는 프로젝트입니다. 머신러닝(LightGBM) 모델을 도입하여 동별 면적, 고도, 과거 침수 이력 등을 기반으로 3시간 단위의 실시간 침수 위험도를 예측합니다. 

특히 `run_pipeline.py`를 통해 실시간 데이터 수집부터 태블로 시각화 데이터 생성까지의 전 과정을 자동화하였습니다.

---

## 📁 폴더 구조

```text
flood-master/
├── config.py                  # API 키 및 경로 설정
├── run_pipeline.py            # ⭐ 실시간 수집~예측~시각화 자동화 파이프라인 (3시간 주기)
├── init_master.py             # 하수관로 위치 마스터 초기 생성
├── fix_master.py              # 위치 마스터 None 좌표 수정
│
├── collect/                   # 실시간 데이터 수집
│   ├── drainpipe_collect.py   # 서울시 하수관로 수위 수집
│   └── rainfall_collect.py    # 서울시 강우량 수집 (병렬 수집 최적화)
│
├── preprocess/                # 데이터 전처리
│   ├── dem_process.py         # DEM 전처리
│   ├── flood_process.py       # 침수 흔적도 전처리
│   ├── merge.py               # 학습 데이터 동별 병합
│   ├── add_dong_area.py       # 동별 면적 계산 및 추가
│   └── realtime_merge.py      # 실시간 데이터 동별 병합
│
├── model/                     # 예측 모델 학습 및 추론
│   ├── features.py            # 변수 생성
│   ├── train_severity.py      # LightGBM 위험도 모델 학습
│   ├── predict_severity.py    # 실시간 데이터 기반 위험도 예측
│   ├── make_tableau_master.py # 태블로 대시보드용 최종 데이터 생성 (시계열 병합 최적화)
│   └── saved/                 # 학습된 모델(.pkl) 저장소
│
└── data/
    ├── raw/                   # 원본 데이터 (대용량 파일 깃허브 미포함)
    │   ├── dem/               # DEM 타일 (37608, 37705, 37709, 37612) × 5년
    │   ├── rainfall/          # 원본 강우량 데이터
    │   ├── drainpipe/         # 원본 하수관로 데이터
    │   ├── flood/             # 침수 흔적도 원본
    │   └── boundary/          # 서울시 행정경계 shp
    │
    ├── processed/             # 전처리 완료 데이터
    │   ├── train_dataset_all_with_area.zip   # 모델 학습용 최종 통합 데이터 (압축 해제 필요)
    │   ├── merged_by_dong_with_area.csv      # 동별 면적 및 과거 이력 병합 데이터
    │   ├── prediction_input_with_area.csv    # 모델 추론용 실시간 입력 데이터
    │   └── risk_output.csv                   # 모델 예측 결과 (위험도 점수 등)
    │
    └── final/                 # 태블로 연결용 최종 산출물 (파이프라인을 통해 자동 갱신)
        ├── tableau_master_dashboard.csv      # 지도, TOP10, 산점도 시각화용 데이터
        └── tableau_timeline.csv              # 시간대별 침수 추이 + 현재 예측값 시계열 데이터
```

### ⚠️ 필수 확인 사항 (압축 해제)
대용량 파일 업로드 제한으로 인해 일부 주요 파일은 분할 및 압축되어 제공됩니다. 프로젝트 실행 및 태블로 연결 전 **반드시 아래 파일들의 압축을 풀어주세요.**
1. `data/processed/train_dataset_all_with_area.zip`
2. `data/processed/train_dataset_all.zip` (해당하는 경우)

---

## 📊 태블로 대시보드 연결 가이드

생성된 `.twb` 대시보드 파일을 사용하려면, 아래의 `.csv` 파일들을 태블로 데이터 원본에 **독립적으로(조인 없이)** 연결해야 합니다.

1. **태블로 마스터 데이터 (공간적 모니터링)**: `data/final/tableau_master_dashboard.csv`
   - 현재 시각 기준 서울시 467개 동의 수위, 강수량, 3시간 뒤 예측 위험도(`RISK_LEVEL`)를 포함합니다.
2. **이전 침수 기록 및 예상 피해도 (시계열 흐름 탐색)**: `data/final/tableau_timeline.csv`
   - 과거부터 미래(예측값)까지 동일 시간대 서울시 평균 데이터를 묶어, 결측치 없이 완벽하게 이어지는 라인 차트용 데이터입니다.
3. **서울시 행정경계 (지도 매핑용)**: `data/raw/boundary/*.shp` 파일

---

## 💾 학습 데이터 (`train_dataset_all_with_area.csv`)

총 **603,708행** / 2021~2025년 / 3시간 단위 (기존 학습 데이터에 동별 면적 특성이 추가되었습니다.)

| 컬럼 | 설명 | 컬럼 | 설명 |
|---|---|---|---|
| EMD_CD | 법정동 코드 | TOTAL_SCALE | 과거 총 침수 규모 (침수심 × 침수면적) |
| EMD_NM | 동 이름 | AVG_DEPTH_PER_AREA | 과거 평균 단위면적당 침수심 |
| DATETIME | 시간 (3시간 단위) | RECENT_YR | 가장 최근 침수 년도 |
| **DONG_AREA** | **동 면적 (m²)** (추가됨) | AVG_WATL | 동별 평균 하수관로 수위 |
| AVG_ELEVATION | 동별 평균 고도 (m) | MAX_WATL | 동별 최대 하수관로 수위 |
| MIN_ELEVATION | 동별 최저 고도 (m) | AVG_RN1 | 동별 평균 강수량 |
| MAX_ELEVATION | 동별 최고 고도 (m) | MAX_RN1 | 동별 최대 강수량 |
| FLOOD_COUNT | 과거 침수 발생 횟수 | TOTAL_RN1 | 동별 총 강수량 |
| AVG_SHIM | 과거 평균 침수심 (m) | YEAR | 연도 |
| MAX_SHIM | 과거 최대 침수심 (m) | RISK_SCORE | **침수 위험도 모델 타겟 라벨** (추가됨) |
| AVG_AREA | 과거 평균 침수면적 (m²) |

---

## 🕒 실시간 예측 입력 데이터 (`prediction_input_with_area.csv`)

`run_pipeline.py` 가동 시 3시간마다 자동 갱신되며 467개 동 전체의 현재 상태를 담고 있습니다.

| 컬럼 | 설명 | 컬럼 | 설명 |
|---|---|---|---|
| EMD_CD | 법정동 코드 | AVG_AREA | 과거 평균 침수면적 (m²) |
| EMD_NM | 동 이름 | TOTAL_SCALE | 과거 총 침수 규모 |
| **DONG_AREA** | **동 면적 (m²)** (추가됨) | AVG_DEPTH_PER_AREA | 과거 평균 단위면적당 침수심 |
| AVG_ELEVATION | 동별 평균 고도 (m) | RECENT_YR | 가장 최근 침수 년도 |
| MIN_ELEVATION | 동별 최저 고도 (m) | AVG_WATL | 현재 동별 평균 하수관로 수위 |
| MAX_ELEVATION | 동별 최고 고도 (m) | MAX_WATL | 현재 동별 최대 하수관로 수위 |
| FLOOD_COUNT | 과거 침수 발생 횟수 | AVG_RN1 | 현재 동별 평균 강수량 |
| AVG_SHIM | 과거 평균 침수심 (m) | MAX_RN1 | 현재 동별 최대 강수량 |
| MAX_SHIM | 과거 최대 침수심 (m) | TOTAL_RN1 | 현재 동별 총 강수량 |

---

## ⚙️ 실행 순서

### 1. 환경 설정 및 압축 해제 (필수)
아래 명령어를 통해 필요한 모든 패키지(`openpyxl`, `shapely`, `pyshp` 포함)를 한 번에 설치하세요.
```bash
python -m venv venv
venv\Scripts\activate
python -m pip install rasterio geopandas numpy pandas requests schedule openpyxl aiohttp tabpy lightgbm scikit-learn shapely pyshp
```
* `data/processed/` 폴더 내의 `.zip` 파일 압축을 모두 해제합니다.

### 2. config.py 설정
```python
SEOUL_API_KEY  = "서울시 API 키"
KAKAO_API_KEY  = "카카오 REST API 키"
```

### 3. 최초 1회 전처리 및 모델 학습
```bash
python init_master.py
python preprocess/dem_process.py
python preprocess/flood_process.py
# (과거 데이터 수집 스크립트 실행 생략)
python preprocess/merge.py
python preprocess/add_dong_area.py       # 동 면적 추가
python model/train_severity.py           # 위험도 모델 학습 및 저장
```

### 4. ⭐ 실시간 데이터 파이프라인 시작 (수집 -> 예측 -> 태블로 갱신)
기존의 복잡했던 PowerShell 스크립트 대신, 파이썬 파일 하나로 전체 프로세스를 자동화했습니다 [file:703]. 
터미널에서 아래 명령어 한 줄만 입력하면 **데이터 수집부터 모델 예측, 태블로 시각화 파일 생성까지 전 과정이 3시간 주기로 무한 반복 실행**됩니다.

```bash
python run_pipeline.py
```

* **파이프라인 작동 순서:**
  1. `drainpipe_collect`, `rainfall_collect`: 서울시 실시간 데이터 병렬 수집
  2. `realtime_merge`: 수집된 실시간 데이터 동별 병합
  3. `add_dong_area`: 동별 면적 데이터 컬럼 매핑
  4. `predict_severity`: LightGBM 모델 기반 3시간 뒤 침수 위험도 예측
  5. `make_tableau_master`: 예측 결과 및 과거 데이터 융합 -> 태블로 연결용 최종 CSV 갱신

---

## 🌐 API 정보

| API | 출처 | 용도 |
|---|---|---|
| 서울시 열린데이터광장 | data.seoul.go.kr | 하수관로 수위, 강우량 수집 |
| 카카오 로컬 API | developers.kakao.com | 주소 지오코딩 |

---

## 🗺️ 좌표계
모든 공간 데이터는 분석을 위해 **EPSG:4326 (WGS84)** 기준으로 통일되었습니다.

| 데이터 | 원본 좌표계 | 변환 후 |
|---|---|---|
| DEM | EPSG:5179 | EPSG:4326 |
| 침수 흔적도 | EPSG:5179 | EPSG:4326 |
| 행정경계 | EPSG:5186 | EPSG:4326 |
| 강우량계 위치 | EPSG:5181 | EPSG:4326 |