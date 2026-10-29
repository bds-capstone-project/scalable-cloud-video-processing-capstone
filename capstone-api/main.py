import os
import uuid
import boto3

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Capstone Video Processing API")

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://main.d3ed6nps7gp8lb.amplifyapp.com"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

BUCKET = "bds-capstone-video-processing-2026"
s3 = boto3.client("s3", region_name="us-east-1")


class UploadRequest(BaseModel):
    filename: str


@app.get("/health")
def health():
    return {"status": "ok", "service": "capstone-video-api"}


@app.post("/upload-url")
def upload_url(request: UploadRequest):
    filename = os.path.basename(request.filename)

    if not filename.lower().endswith(".mp4"):
        raise HTTPException(400, "Only MP4 files are supported")

    job_id = str(uuid.uuid4())
    key = f"input/{job_id}.mp4"

    url = s3.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": BUCKET,
            "Key": key,
            "ContentType": "video/mp4",
        },
        ExpiresIn=900,
    )

    return {
        "job_id": job_id,
        "upload_url": url,
        "content_type": "video/mp4",
    }


@app.get("/status/{job_id}")
def status(job_id: uuid.UUID):
    output_key = f"output/{job_id}.mp4"

    try:
        s3.head_object(Bucket=BUCKET, Key=output_key)
        return {"job_id": str(job_id), "status": "completed"}
    except s3.exceptions.ClientError as exc:
        if exc.response["Error"]["Code"] in ("404", "NoSuchKey"):
            return {"job_id": str(job_id), "status": "processing"}
        raise HTTPException(502, "Unable to check processing status")


@app.get("/download-url/{job_id}")
def download_url(job_id: uuid.UUID):
    output_key = f"output/{job_id}.mp4"

    try:
        s3.head_object(Bucket=BUCKET, Key=output_key)
    except s3.exceptions.ClientError as exc:
        if exc.response["Error"]["Code"] in ("404", "NoSuchKey"):
            raise HTTPException(404, "Video is not ready")
        raise HTTPException(502, "Unable to check output")

    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": BUCKET, "Key": output_key},
        ExpiresIn=900,
    )

    return {"download_url": url}
