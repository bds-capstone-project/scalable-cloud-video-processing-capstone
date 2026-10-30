import boto3
import time
import uuid
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

BUCKET = "bds-capstone-video-processing-2026"
VIDEO_DIR = Path("input")
POLL_INTERVAL = 5

s3 = boto3.client("s3")
videos = sorted(VIDEO_DIR.glob("*.mp4"))

if len(videos) != 8:
    raise ValueError("Exactly 16 MP4 videos are required.")

jobs = []

# Generate unique job IDs for this test
for video in videos:
    job_id = str(uuid.uuid4())
    jobs.append({
        "file": video,
        "input": f"input/{job_id}.mp4",
        "output": f"output/{job_id}.mp4"
    })

def upload(job):
    s3.upload_file(
        str(job["file"]),
        BUCKET,
        job["input"]
    )
    print(f"Uploaded: {job['file'].name}")

def output_exists(job):
    try:
        s3.head_object(Bucket=BUCKET, Key=job["output"])
        return True
    except s3.exceptions.ClientError as e:
        if e.response["Error"]["Code"] in ("404", "NoSuchKey"):
            return False
        raise

print("Starting performance test...")
start = time.perf_counter()

# Upload all 8 videos
with ThreadPoolExecutor(max_workers=8) as executor:
    list(executor.map(upload, jobs))

print("All videos uploaded. Waiting for processing...")

completed = set()

while len(completed) < len(jobs):
    for job in jobs:
        key = job["output"]

        if key not in completed and output_exists(job):
            completed.add(key)
            print(f"Completed: {len(completed)}/8")

    if len(completed) < len(jobs):
        time.sleep(POLL_INTERVAL)

elapsed = time.perf_counter() - start
throughput = len(jobs) / elapsed

print("\n--- PERFORMANCE RESULTS ---")
print(f"Videos processed: {len(jobs)}")
print(f"Total time: {elapsed:.2f} seconds")
print(f"Total time: {elapsed / 60:.2f} minutes")
print(f"Throughput: {throughput:.4f} videos/second")
