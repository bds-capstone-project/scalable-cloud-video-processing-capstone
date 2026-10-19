import time
import sys

from config.config import INPUT_DIR
from job_queue.queue_manager import add_job, queue_size, wait_for_all_jobs
from scaling.autoscaler import AutoScaler


# Force UTF-8 output so symbols like → work on Windows and localhost
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def main():

    print("\n==============================")
    print(" CLOUD VIDEO PROCESSING DEMO")
    print("==============================\n")

    videos = list(INPUT_DIR.glob("*.mp4"))

    if not videos:
        print("No MP4 videos found in input/")
        return

    print(f"Found {len(videos)} videos.\n")

    # Start autoscaler with minimum workers
    scaler = AutoScaler()

    # Add videos to the processing queue
    for video in videos:

        add_job(video)

        # Check whether more workers are needed
        scaler.evaluate(queue_size())

        time.sleep(0.2)

    print("\nAll videos submitted.")
    print(f"Queue size: {queue_size()}")
    print(f"Active workers: {scaler.worker_count()}\n")

    # Monitor queue while jobs are waiting
    while queue_size() > 0:

        print(
            f"[STATUS] Queue: {queue_size()} | "
            f"Workers: {scaler.worker_count()}"
        )

        scaler.evaluate(queue_size())

        time.sleep(2)

    print("\nAll queued jobs assigned.")
    print("Waiting for processing to finish...\n")

    # Wait until workers actually finish every job
    wait_for_all_jobs()

    print("\n==============================")
    print(" ALL VIDEOS PROCESSED")
    print("==============================")

    print("\nDemo complete.")


if __name__ == "__main__":
    main()
