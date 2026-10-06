

import threading

from queue.queue_manager import (
    get_job,
    complete_job
)

from worker.video_processor import process_video
from config.config import OUTPUT_DIR


class VideoWorker(threading.Thread):

    def __init__(self, worker_id):
        super().__init__(daemon=True)

        self.worker_id = worker_id
        self.running = True

    def run(self):

        print(f"[WORKER-{self.worker_id}] Started")

        while self.running:

            video = get_job()

            try:
                print(
                    f"[WORKER-{self.worker_id}] "
                    f"Processing {video.name}"
                )

                output = process_video(
                    video,
                    OUTPUT_DIR
                )

                print(
                    f"[WORKER-{self.worker_id}] "
                    f"Completed → {output.name}"
                )

            except Exception as error:

                print(
                    f"[WORKER-{self.worker_id}] "
                    f"FAILED: {error}"
                )

            finally:
                complete_job()

    def stop(self):
        self.running = False
