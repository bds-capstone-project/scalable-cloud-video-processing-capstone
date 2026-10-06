

import time

from config.config import INPUT_DIR
from job_queue.queue_manager import add_job, queue_size
from scaling.autoscaler import AutoScaler


def main():

    print("\n==============================")
    print(" CLOUD VIDEO PROCESSING DEMO")
    print("==============================\n")

    videos = list(INPUT_DIR.glob("*.mp4"))

    if not videos:
        print("No MP4 videos found in input/")
        return

    print(f"Found {len(videos)} videos.\n")

    scaler = AutoScaler()

    for video in videos:

        add_job(video)

        scaler.evaluate(queue_size())

        time.sleep(0.2)

    print("\nAll videos submitted.")
    print(f"Queue size: {queue_size()}")
    print(f"Active workers: {scaler.worker_count()}")

    while queue_size() > 0:
        print(
            f"[STATUS] Queue: {queue_size()} | "
            f"Workers: {scaler.worker_count()}"
        )

        scaler.evaluate(queue_size())

        time.sleep(2)

    print("\nAll queued jobs assigned.")
    print("Waiting for processing to finish...")

    time.sleep(5)

    print("\nDemo complete.")


if __name__ == "__main__":
    main()
