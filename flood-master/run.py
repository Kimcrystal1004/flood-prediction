# run.py
import schedule
import time
from collect.drainpipe_collect import collect_train as drainpipe_train
from collect.drainpipe_collect import collect_realtime as drainpipe_realtime
from collect.rainfall_collect import collect_train as rainfall_train
from collect.rainfall_collect import collect_realtime as rainfall_realtime
from preprocess.realtime_merge import merge_realtime


# ── 학습 데이터 수집 (기간 지정 후 주석 해제) ──────────────
# drainpipe_train("2026010100", "2026052300")
# rainfall_train("20260101", "20260523")


def realtime_job():
    drainpipe_realtime()
    rainfall_realtime()
    merge_realtime()


if __name__ == "__main__":
    print("실시간 수집 시작 (Ctrl+C로 종료)")

    # 즉시 1회 실행
    realtime_job()

    # 하수관로 3시간마다, 강우량 6시간마다
    schedule.every(3).hours.do(drainpipe_realtime)
    schedule.every(6).hours.do(rainfall_realtime)
    schedule.every(6).hours.do(merge_realtime)

    while True:
        schedule.run_pending()
        time.sleep(1)