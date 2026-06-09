import os
import sys
import time
from datetime import datetime

# 기준 경로 강제 추가 (ModuleNotFoundError 해결 핵심)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from collect.drainpipe_collect import collect_realtime as drainpipe_rt
from collect.rainfall_collect import collect_realtime as rainfall_rt
from preprocess.realtime_merge import merge_realtime
# 모듈 방식이 아닌 스크립트 실행을 위한 os.system
import subprocess

def run_job():
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 파이프라인 시작...")
    
    print("1. 실시간 데이터 수집 시작...")
    drainpipe_rt()
    rainfall_rt()
    
    print("2. 실시간 데이터 동별 병합...")
    merge_realtime()
    
    print("3. 동별 면적 데이터 추가...")
    subprocess.run(["python", os.path.join(BASE_DIR, "preprocess", "add_dong_area.py")])
    
    print("4. 침수 위험도 모델 예측...")
    subprocess.run(["python", os.path.join(BASE_DIR, "model", "predict_severity.py")])
    
    print("5. 태블로 마스터 대시보드 갱신...")
    subprocess.run(["python", os.path.join(BASE_DIR, "model", "make_tableau_master.py")])
    
    print("=== 파이프라인 1사이클 완료! ===\n")

if __name__ == "__main__":
    while True:
        run_job()
        print("3시간 대기 중... (종료는 Ctrl+C)")
        time.sleep(10800) # 3시간(10800초) 대기