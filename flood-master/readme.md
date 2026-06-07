# 서울시 침수 위험도 예측 프로젝트

## 프로젝트 개요
서울시 하수관로 수위, 강우량, DEM(수치표고모델), 침수 흔적도 데이터를 활용하여
동 단위 실시간 침수 위험도를 예측하고 태블로 대시보드로 시각화하는 프로젝트입니다.

---

## 폴더 구조

~~~
flood/
├── config.py                  # API 키 및 경로 설정
├── run.py                     # 실시간 수집 트리거
├── init_master.py             # 하수관로 위치 마스터 초기 생성
├── fix_master.py              # 위치 마스터 None 좌표 수정
│
├── collect/                   # 실시간 데이터 수집
│   ├── drainpipe_collect.py   # 서울시 하수관로 수위 수집
│   └── rainfall_collect.py    # 서울시 강우량 수집
│
├── historical/                # 과거 학습 데이터 처리
│   ├── drainpipe_historical.py
│   └── rainfall_historical.py
│
├── preprocess/                # 데이터 전처리
│   ├── dem_process.py         # DEM 전처리
│   ├── flood_process.py       # 침수 흔적도 전처리
│   ├── merge.py               # 학습 데이터 동별 병합
│   └── realtime_merge.py      # 실시간 데이터 동별 병합
│
└── data/
    ├── raw/                   # 원본 데이터 (깃허브 미포함)
    │   ├── dem/               # DEM 타일 (37608, 37705, 37709, 37612) × 5년
    │   ├── rainfall/
    │   │   ├── 1h/            # 1시간 누적 강우량
    │   │   ├── 3h/            # 3시간 누적 강우량 (학습용)
    │   │   └── historical/    # 월별 원본 CSV
    │   ├── drainpipe/
    │   │   └── historical/    # 연도별 원본 ZIP
    │   ├── flood/             # 침수 흔적도 원본
    │   └── boundary/          # 서울시 행정경계 shp
    │
    └── processed/             # 전처리 완료 데이터 (깃허브 미포함)
        ├── dem_seoul_{year}.csv          # 연도별 서울 전체 픽셀별 위경도 + 고도값
        ├── location_master.csv           # 하수관로 관측소 위치 마스터 (581개)
        ├── gauge_to_dong.csv             # 강우량계 → 법정동 코드 매핑
        ├── pipe_to_dong.csv              # 하수관로 관측소 → 법정동 코드 매핑
        ├── flood_by_dong_{year}.csv      # 연도별 침수 흔적도 동별 집계
        ├── merged_by_dong_{year}.csv     # 연도별 DEM + 침수흔적도 병합 (467개 동)
        ├── train_dataset_{year}.csv      # 연도별 최종 학습 데이터
        ├── train_dataset_all.csv         # 전체 학습 데이터 (603,708행, 2021~2025년)
        └── prediction_input.csv          # 실시간 모델 입력용 (467개 동, 매 3시간 갱신)
~~~

---

## 학습 데이터 (train_dataset_all.csv)

총 **603,708행** / 2021~2025년 / 3시간 단위

| 컬럼 | 설명 |
|---|---|
| EMD_CD | 법정동 코드 |
| EMD_NM | 동 이름 |
| DATETIME | 시간 (3시간 단위) |
| AVG_ELEVATION | 동별 평균 고도 (m) |
| MIN_ELEVATION | 동별 최저 고도 (m) |
| MAX_ELEVATION | 동별 최고 고도 (m) |
| FLOOD_COUNT | 과거 침수 발생 횟수 |
| AVG_SHIM | 과거 평균 침수심 (m) |
| MAX_SHIM | 과거 최대 침수심 (m) |
| AVG_AREA | 과거 평균 침수면적 (m²) |
| TOTAL_SCALE | 과거 총 침수 규모 (침수심 × 침수면적) |
| AVG_DEPTH_PER_AREA | 과거 평균 단위면적당 침수심 |
| RECENT_YR | 가장 최근 침수 년도 |
| AVG_WATL | 동별 평균 하수관로 수위 |
| MAX_WATL | 동별 최대 하수관로 수위 |
| AVG_RN1 | 동별 평균 강수량 |
| MAX_RN1 | 동별 최대 강수량 |
| TOTAL_RN1 | 동별 총 강수량 |
| YEAR | 연도 |

---

## 실시간 예측 입력 데이터 (prediction_input.csv)

`run.py` 실행 시 3시간마다 자동 갱신되며 467개 동 전체의 현재 상태를 담고 있음.

| 컬럼 | 설명 |
|---|---|
| EMD_CD | 법정동 코드 |
| EMD_NM | 동 이름 |
| AVG_ELEVATION | 동별 평균 고도 (m) |
| MIN_ELEVATION | 동별 최저 고도 (m) |
| MAX_ELEVATION | 동별 최고 고도 (m) |
| FLOOD_COUNT | 과거 침수 발생 횟수 |
| AVG_SHIM | 과거 평균 침수심 (m) |
| MAX_SHIM | 과거 최대 침수심 (m) |
| AVG_AREA | 과거 평균 침수면적 (m²) |
| TOTAL_SCALE | 과거 총 침수 규모 |
| AVG_DEPTH_PER_AREA | 과거 평균 단위면적당 침수심 |
| RECENT_YR | 가장 최근 침수 년도 |
| AVG_WATL | 현재 동별 평균 하수관로 수위 |
| MAX_WATL | 현재 동별 최대 하수관로 수위 |
| AVG_RN1 | 현재 동별 평균 강수량 |
| MAX_RN1 | 현재 동별 최대 강수량 |
| TOTAL_RN1 | 현재 동별 총 강수량 |

---

## 실행 순서

### 1. 환경 설정
~~~bash
python -m venv venv
venv\Scripts\activate
python -m pip install rasterio geopandas numpy pandas requests schedule openpyxl aiohttp tabpy
~~~

### 2. config.py 설정
~~~python
SEOUL_API_KEY  = "서울시 API 키"
KAKAO_API_KEY  = "카카오 REST API 키"
~~~

### 3. 최초 1회 전처리
~~~bash
python init_master.py
python preprocess/dem_process.py
python preprocess/flood_process.py
python historical/drainpipe_historical.py
python historical/rainfall_historical.py
python preprocess/merge.py
~~~

### 4. 실시간 수집 시작
~~~bash
python run.py
~~~
- 하수관로 + 강우량 동시 수집 (3시간마다)
- `prediction_input.csv` 자동 갱신
- `Ctrl+C` 로 종료

---

## API 정보

| API | 출처 | 용도 |
|---|---|---|
| 서울시 열린데이터광장 | data.seoul.go.kr | 하수관로 수위, 강우량 수집 |
| 카카오 로컬 API | developers.kakao.com | 주소 지오코딩 |

---

## 좌표계
모든 데이터는 **EPSG:4326 (WGS84)** 기준으로 통일

| 데이터 | 원본 좌표계 | 변환 후 |
|---|---|---|
| DEM | EPSG:5179 | EPSG:4326 |
| 침수 흔적도 | EPSG:5179 | EPSG:4326 |
| 행정경계 | EPSG:5186 | EPSG:4326 |
| 강우량계 위치 | EPSG:5181 | EPSG:4326 |
