from worker.worker import VideoWorker

from config.config import (
    MIN_WORKERS,
    MAX_WORKERS,
    SCALE_UP_THRESHOLD
)


class AutoScaler:

    def __init__(self):
        self.workers = []
        self.worker_counter = 0

        for _ in range(MIN_WORKERS):
            self.add_worker()

    def add_worker(self):

        if len(self.workers) >= MAX_WORKERS:
            return

        self.worker_counter += 1

        worker = VideoWorker(self.worker_counter)
        worker.start()

        self.workers.append(worker)

        print(
            f"[AUTOSCALER] Scale UP → "
            f"{len(self.workers)} workers"
        )

    def evaluate(self, queue_size):

        if (
            queue_size >= SCALE_UP_THRESHOLD
            and len(self.workers) < MAX_WORKERS
        ):
            self.add_worker()

    def worker_count(self):
        return len(self.workers)
