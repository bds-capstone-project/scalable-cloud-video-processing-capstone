

from queue import Queue

job_queue = Queue()


def add_job(video_path):
    job_queue.put(video_path)
    print(f"[QUEUE] Added: {video_path.name}")


def get_job():
    return job_queue.get()


def complete_job():
    job_queue.task_done()

def wait_for_all_jobs():
    job_queue.join()

def queue_size():
    return job_queue.qsize()
