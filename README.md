# 서울시 침수 위험도 예측 프로젝트

## 프로젝트 개요
서울시 하수관로 수위, 강우량, DEM(수치표고모델), 침수 흔적도 데이터를 활용하여 동 단위 실시간 침수 위험도를 예측하고, 이를 태블로 대시보드로 시각화하는 프로젝트입니다. 머신러닝(LightGBM) 모델을 도입하여 동별 면적, 고도, 과거 침수 이력 등을 기반으로 3시간 단위의 실시간 침수 위험도를 예측합니다.

***

## 📁 폴더 구조

~~~
flood-master/
├── config.py                  # API 키 및 경로 설정
├── run.py                     # 실시간 수집 및 예측 트리거 (3시간 단위)
├── init_master.py             # 하수관로 위치 마스터 초기 생성
├── fix_master.py              # 위치 마스터 None 좌표 수정
│
├── collect/                   # 실시간 데이터 수집
│   ├── drainpipe_collect.py   # 서울시 하수관로 수위 수집
│   └── rainfall_collect.py    # 서울시 강우량 수집
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
│   ├── make_tableau_master.py # 태블로 대시보드용 최종 데이터 생성
│   └── saved/                 # 학습된 모델(.pkl) 저장소
│
└── data/
    ├── raw/                   # 원본 데이터 (깃허브 미포함)
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
    └── final/                 # 태블로 연결용 최종 산출물
        ├── tableau_severity_map.csv          # 태블로 지도 시각화용 데이터
        └── tableau_master_dashboard.zip      # 태블로 전체 대시보드 연결용 마스터 데이터 (압축 해제 필요)
~~~

### ⚠️ 필수 확인 사항 (압축 해제)
대용량 파일 업로드 제한으로 인해 일부 주요 파일은 분할 및 압축되어 제공됩니다. 프로젝트 실행 및 태블로 연결 전 **반드시 아래 파일들의 압축을 풀어주세요.**
1. `data/processed/train_dataset_all_with_area.zip`
2. `data/processed/train_dataset_all.zip`
3. `data/final/tableau_master_dashboard.zip`

***

## 📊 태블로 대시보드 연결 가이드

생성된 `.twb` 대시보드 파일을 사용하려면, 아래의 `.csv` 파일들을 태블로 데이터 원본에 직접 연결해야 합니다.

1. **태블로 마스터 데이터 (전체 대시보드용)**: `data/final/tableau_master_dashboard.csv` (zip 파일 압축 해제 후 생성됨)
2. **태블로 지도 시각화용 데이터**: `data/final/tableau_severity_map.csv`

***

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

***

## 🕒 실시간 예측 입력 데이터 (`prediction_input_with_area.csv`)

3시간마다 자동 갱신되며 467개 동 전체의 현재 상태를 담고 있습니다. 모델은 이 데이터를 입력받아 위험도를 예측합니다.

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

***

## ⚙️ 실행 순서

### 1. 환경 설정 및 압축 해제 (필수)
아래 명령어를 통해 필요한 모든 패키지(`openpyxl`, `shapely`, `pyshp` 포함)를 한 번에 설치하세요.
~~~bash
python -m venv venv
venv\Scripts\activate
python -m pip install rasterio geopandas numpy pandas requests schedule openpyxl aiohttp tabpy lightgbm scikit-learn shapely pyshp
~~~
* `data/processed/`와 `data/final/` 폴더 내의 `.zip` 파일 압축을 모두 해제합니다.

### 2. config.py 설정
~~~python
SEOUL_API_KEY  = "서울시 API 키"
KAKAO_API_KEY  = "카카오 REST API 키"
~~~

### 3. 최초 1회 전처리 및 모델 학습
~~~bash
python init_master.py
python preprocess/dem_process.py
python preprocess/flood_process.py
# (과거 데이터 수집 스크립트 실행 생략)
python preprocess/merge.py
python preprocess/add_dong_area.py       # 동 면적 추가
python model/train_severity.py           # 위험도 모델 학습 및 저장
~~~

### 4. 실시간 데이터 파이프라인 시작 (수집 -> 예측 -> 태블로 갱신)
파이썬 코드를 수정할 필요 없이, **PowerShell(파워쉘)에서 아래 코드를 그대로 복사+붙여넣기** 하시면 파이프라인 전체가 3시간 주기로 무한 반복 실행됩니다.

~~~powershell
$env:PYTHONPATH = (Get-Location).Path
while ($true) {
    Write-Host "1. 실시간 데이터 수집 시작..." -ForegroundColor Green
    python -c "from collect.drainpipe_collect import collect_realtime; collect_realtime()"
    python -c "from collect.rainfall_collect import collect_realtime; collect_realtime()"
    
    Write-Host "2. 실시간 데이터 동별 병합..." -ForegroundColor Green
    python -c "from preprocess.realtime_merge import merge_realtime; merge_realtime()"
    
    Write-Host "3. 동별 면적 데이터 추가 (면적 컬럼 매핑)..." -ForegroundColor Green
    python preprocess/add_dong_area.py
    
    Write-Host "4. 침수 위험도 모델 예측 (LGBM)..." -ForegroundColor Green
    python model/predict_severity.py
    
    Write-Host "5. 태블로 마스터 대시보드 데이터 갱신..." -ForegroundColor Green
    python model/make_tableau_master.py
    
    Write-Host "=== 파이프라인 1사이클 완료! 3시간 대기 (종료는 Ctrl+C) ===" -ForegroundColor Yellow
    Start-Sleep -Seconds 10800
}
~~~

***

## 🌐 API 정보

| API | 출처 | 용도 |
|---|---|---|
| 서울시 열린데이터광장 | data.seoul.go.kr | 하수관로 수위, 강우량 수집 |
| 카카오 로컬 API | developers.kakao.com | 주소 지오코딩 |

***

## 🗺️ 좌표계
모든 공간 데이터는 분석을 위해 **EPSG:4326 (WGS84)** 기준으로 통일되었습니다.

| 데이터 | 원본 좌표계 | 변환 후 |
|---|---|---|
| DEM | EPSG:5179 | EPSG:4326 |
| 침수 흔적도 | EPSG:5179 | EPSG:4326 |
| 행정경계 | EPSG:5186 | EPSG:4326 |
| 강우량계 위치 | EPSG:5181 | EPSG:4326 |