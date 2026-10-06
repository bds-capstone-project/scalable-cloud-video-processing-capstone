# Scalable Cloud Video Processing with Automatic Scaling and Fault Recovery

Capstone project implementing a cloud-based video processing system using Python,ffmpeg and AWS.

## Overview

Video processing jobs are submitted to a queue and processed in parallel by multiple cloud workers.

The system is designed to:

- Process video jobs across multiple workers
- Automatically scale workers according to workload
- Recover unfinished jobs after worker failure
- Measure performance, scaling behaviour, recovery, and estimated cloud cost

## Architecture

Video Files → Queue → Multiple Workers → Processed Videos

## Team

- Aaron Mathews Molayal — Technical Lead / Cloud Engineer
- Tuan Minh — Backend & Reliability
- Hayyan Mohammad — Performance & Evaluation
- Chalisa — Web Interface & Documentation
