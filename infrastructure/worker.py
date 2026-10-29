#!/usr/bin/env python3
"""SQS -> S3 -> FFmpeg -> S3 worker for the BDS capstone."""
import json
import logging
import os
import signal
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from urllib.parse import unquote_plus

import boto3

REGION = os.environ.get('AWS_REGION', 'us-east-1')
BUCKET = os.environ.get('VIDEO_BUCKET', 'bds-capstone-video-processing-2026')
QUEUE_NAME = os.environ.get('VIDEO_QUEUE', 'bds-capstone-queue')
VISIBILITY_SECONDS = 300
HEARTBEAT_SECONDS = 60

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('aws-worker')
s3 = boto3.client('s3', region_name=REGION)
sqs = boto3.client('sqs', region_name=REGION)
shutdown_requested = False


def handle_shutdown(signum, frame):
    global shutdown_requested
    shutdown_requested = True
    log.warning('Received signal %s; will finish current job and stop polling', signum)


def parse_job(body):
    payload = json.loads(body)
    # Supports both our simple JSON jobs and direct S3 event notifications.
    if 'Records' in payload:
        record = payload['Records'][0]
        bucket = record['s3']['bucket']['name']
        key = unquote_plus(record['s3']['object']['key'])
    else:
        bucket = payload.get('bucket', BUCKET)
        key = payload['key']
    if bucket != BUCKET or not key.startswith('input/') or key.endswith('/'):
        raise ValueError(f'Unexpected bucket or input key: {bucket}/{key}')
    return key


def extend_visibility(queue_url, receipt_handle, stop_event):
    while not stop_event.wait(HEARTBEAT_SECONDS):
        try:
            sqs.change_message_visibility(
                QueueUrl=queue_url,
                ReceiptHandle=receipt_handle,
                VisibilityTimeout=VISIBILITY_SECONDS,
            )
        except Exception:
            log.exception('Failed to extend message visibility')


def process_job(message, queue_url):
    receipt_handle = message['ReceiptHandle']
    stop_event = threading.Event()
    heartbeat = threading.Thread(
        target=extend_visibility,
        args=(queue_url, receipt_handle, stop_event),
        daemon=True,
    )
    heartbeat.start()
    try:
        key = parse_job(message['Body'])
        # Deterministic output path: retrying a job overwrites the same result.
        relative = key[len('input/'):]
        output_key = 'output/' + str(Path(relative).with_suffix('.mp4'))
        with tempfile.TemporaryDirectory(prefix='capstone-') as temp_dir:
            source = Path(temp_dir) / 'source.mp4'
            target = Path(temp_dir) / 'processed.mp4'
            log.info('Downloading s3://%s/%s', BUCKET, key)
            s3.download_file(BUCKET, key, str(source))
            command = [
                'ffmpeg', '-hide_banner', '-nostdin', '-y',
                '-i', str(source), '-vf', 'scale=-2:720',
                '-c:v', 'libx264', '-crf', '28', '-preset', 'fast',
                '-c:a', 'aac', '-b:a', '128k', str(target),
            ]
            subprocess.run(command, check=True)
            log.info('Uploading s3://%s/%s', BUCKET, output_key)
            s3.upload_file(str(target), BUCKET, output_key)
        sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)
        log.info('Completed %s -> %s; message deleted', key, output_key)
    finally:
        stop_event.set()
        heartbeat.join(timeout=5)


def main():
    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)
    queue_url = sqs.get_queue_url(QueueName=QUEUE_NAME)['QueueUrl']
    log.info('Worker started. Region=%s Bucket=%s Queue=%s', REGION, BUCKET, QUEUE_NAME)

    while not shutdown_requested:
        try:
            response = sqs.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=20,
                VisibilityTimeout=VISIBILITY_SECONDS,
            )
            for message in response.get('Messages', []):
                if shutdown_requested:
                    # We received a job just as shutdown was requested.
                    # Make it immediately available for another worker.
                    try:
                        sqs.change_message_visibility(
                            QueueUrl=queue_url,
                            ReceiptHandle=message['ReceiptHandle'],
                            VisibilityTimeout=0,
                        )
                    except Exception:
                        log.exception('Could not release job during shutdown; SQS will retry it')
                    break
                try:
                    process_job(message, queue_url)
                except Exception:
                    log.exception('Job failed; leaving message for SQS retry / DLQ')
        except Exception:
            if shutdown_requested:
                break
            log.exception('SQS polling failed; retrying')
            time.sleep(10)

    log.info('Worker stopped gracefully')


if __name__ == '__main__':
    main()
