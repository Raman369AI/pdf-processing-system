# DEVELOPMENT.md

This file provides development guidance when working with code in this repository.

## Repository Overview

A FastAPI-based PDF processing system with Celery task queue, Redis backend, and standalone file monitoring. Processes PDFs with field extraction and provides a web interface for managing results. Fault-tolerant and scalable architecture.

## Development Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Start Redis (required for Celery)
redis-server

# Start Celery worker (in separate terminal)
celery -A worker worker --loglevel=info

# Start PDF monitor service (in separate terminal)
python pdf_monitor.py

# Process existing PDFs (one-time utility)
python process_existing.py

# Run the FastAPI application
python main.py

# Access web interface
http://localhost:8000
```

## Architecture

**Separated Services Architecture:**
- **main.py**: FastAPI web application (HTTP API only, no file watching)
- **worker.py**: Celery worker for PDF processing tasks
- **pdf_monitor.py**: Standalone file system monitoring service
- **process_existing.py**: Utility script for processing existing PDFs
- **Redis**: Message broker and result backend for Celery
- **SQLite**: Persistent storage for processed PDF data

## Key Components

- **Fault-tolerant processing**: Celery with Redis backend provides persistence and retry logic
- **Scalable workers**: Multiple Celery workers can process PDFs concurrently
- **Separated concerns**: File monitoring, web API, and processing are independent services
- **Database-centric**: All PDF data stored in database, no in-memory state
- **Async SQLite**: Database operations with locking to prevent conflicts
- **Multi-worker safe**: FastAPI can run multiple workers without conflicts

## Service Dependencies

1. **Redis**: Must be running for Celery communication
2. **Celery Worker**: Must be running to process PDF tasks
3. **PDF Monitor**: Should be running to detect new files
4. **FastAPI**: Web interface and API endpoints

## Deployment Notes

- Each service can be containerized independently
- Scale FastAPI workers horizontally without conflicts
- Scale Celery workers based on processing load
- Single PDF monitor instance per deployment
- Redis provides persistence across restarts