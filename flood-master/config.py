# config.py
import os

# ── API 키 ────────────────────────────────────────────────
SEOUL_API_KEY    = "6e58416e42616c69313030534b754d6a"
KAKAO_API_KEY    = "86e2e124ce500481b611eb28adceb27a"
WEATHER_API_KEY  = "61ae1e6ffafafd57ff395f93c232a58a0cddb2520ee0ed8b120caad89efcb9bb"

# ── 경로 설정 ─────────────────────────────────────────────
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
DATA_DIR      = os.path.join(BASE_DIR, "data")
RAW_DIR       = os.path.join(DATA_DIR, "raw")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")

DEM_DIR       = os.path.join(RAW_DIR, "dem")
RAINFALL_DIR  = os.path.join(RAW_DIR, "rainfall")
DRAINPIPE_DIR = os.path.join(RAW_DIR, "drainpipe")
FLOOD_DIR     = os.path.join(RAW_DIR, "flood")
BOUNDARY_DIR  = os.path.join(RAW_DIR, "boundary")

# ── 파일 경로 ─────────────────────────────────────────────
DEM_FILES = [
    os.path.join(DEM_DIR, "(B080)공개DEM_37608_img_2025.zip"),
    os.path.join(DEM_DIR, "(B080)공개DEM_37705_img_2025.zip"),
    os.path.join(DEM_DIR, "(B080)공개DEM_37709_img_2025.zip"),
    os.path.join(DEM_DIR, "(B080)공개DEM_37612_img_2025.zip"),
]
DEM_IMG_NAMES = [
    "37608/37608.img",
    "37705/37705.img",
    "37709/37709.img",
    "37612/37612.img",
]

MASTER_FILE   = os.path.join(PROCESSED_DIR, "location_master.csv")
DEM_CSV       = os.path.join(PROCESSED_DIR, "dem_seoul.csv")
FLOOD_FILE    = os.path.join(FLOOD_DIR, "flood_trace_seoul_2025.zip")
BOUNDARY_FILE = os.path.join(BOUNDARY_DIR, "LSMD_ADM_SECT_UMD.zip")

# ── 서울시 API 설정 ───────────────────────────────────────
DISTRICT_CODES = [str(i).zfill(2) for i in range(1, 26)]