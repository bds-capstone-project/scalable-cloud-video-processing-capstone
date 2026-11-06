Scalable Cloud Video Processing
AWS-based MP4 processing prototype using a FastAPI backend, S3 storage, an SQS job queue, and EC2 workers running FFmpeg. Worker capacity is managed through EC2 Auto Scaling and CloudWatch.
Code structure
capstone-api/main.py          FastAPI upload URL, status, download URL and health endpoints
frontend/app.js               Browser uploads, status polling and downloads
infrastructure/worker.py      SQS consumer and FFmpeg processing worker
planning/performance_test.py  Eight-video fixed-worker benchmark script
How it works
1. The frontend requests a presigned upload URL from FastAPI.
2. The browser uploads an MP4 directly to S3 (input/<job_id>.mp4).
3. An S3 ObjectCreated notification places a job message in SQS.
4. An EC2 worker reads the message, downloads the video and transcodes it with FFmpeg.
5. The worker uploads output/<job_id>.mp4 to S3, then deletes the SQS message.
6. The frontend polls the status endpoint and requests a download URL when the output is available.
The worker extends SQS message visibility while processing. If it stops before deleting the message, SQS can make the job available for retry.
API endpoints
Method	Endpoint	Purpose
POST	/upload-url	Return job ID and presigned S3 upload URL
GET	/status/{job_id}	Check whether the output exists
GET	/download-url/{job_id}	Return presigned download URL
GET	/health	Health check


Requirements and configuration
- Backend: Python, FastAPI, boto3 and an AWS identity with appropriate S3 permissions.
- Worker: Python, boto3, FFmpeg, S3/SQS permissions and access to the configured queue.
- Frontend: JavaScript; configured to call the deployed API endpoint.
- AWS: S3 bucket, S3-to-SQS event notification, SQS queue, EC2 worker instances/Auto Scaling Group, CloudWatch scaling alarms, and API hosting/routing.
Worker environment variables:
AWS_REGION=us-east-1
VIDEO_BUCKET=<your-s3-bucket>
VIDEO_QUEUE=<your-sqs-queue-name>
These values must match your AWS resources. Deployment requires configuring the AWS services and IAM permissions; this repository is not a one-command infrastructure deployment. Do not commit AWS credentials.
