# Deployment Guide

## Overview

This guide covers various deployment options for the PDF Processing System, from local development to production environments.

## Local Development

### Quick Start
```bash
# Clone and setup
git clone https://github.com/Raman369AI/pdf-processing-system.git
cd pdf-processing-system
pip install -r requirements.txt

# Run application
python main.py
```

### Development with Virtual Environment
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run application
python main.py
```

---

## Production Deployment

### 1. Basic Production Setup

#### Using Uvicorn
```bash
# Install production dependencies
pip install uvicorn[standard]

# Run with production settings
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

#### Using Gunicorn + Uvicorn Workers
```bash
# Install Gunicorn
pip install gunicorn

# Run with Gunicorn
gunicorn main:app -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker
```

### 2. Environment Configuration

#### Create Production Environment File
```bash
# Create .env file
cat > .env << EOF
DATABASE_URL=sqlite:///./pdf_data.db
PDF_FOLDER_PATH=./pdfs
HOST=0.0.0.0
PORT=8000
WORKERS=4
DEBUG=False
EOF
```

#### Update main.py for Environment Variables
```python
import os
from dotenv import load_dotenv

load_dotenv()

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./pdf_data.db")
PDF_FOLDER_PATH = os.getenv("PDF_FOLDER_PATH", "./pdfs")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
```

---

## Docker Deployment

### 1. Basic Dockerfile

```dockerfile
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p pdfs static

# Expose port
EXPOSE 8000

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser
RUN chown -R appuser:appuser /app
USER appuser

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. Docker Compose Setup

```yaml
# docker-compose.yml
version: '3.8'

services:
  pdf-processor:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./pdfs:/app/pdfs
      - ./pdf_data.db:/app/pdf_data.db
    environment:
      - DATABASE_URL=sqlite:///./pdf_data.db
      - PDF_FOLDER_PATH=/app/pdfs
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - pdf-processor
    restart: unless-stopped
```

### 3. Build and Run with Docker

```bash
# Build image
docker build -t pdf-processing-system .

# Run container
docker run -d \
  --name pdf-processor \
  -p 8000:8000 \
  -v $(pwd)/pdfs:/app/pdfs \
  -v $(pwd)/pdf_data.db:/app/pdf_data.db \
  pdf-processing-system

# Or use docker-compose
docker-compose up -d
```

---

## Reverse Proxy Setup

### Nginx Configuration

```nginx
# /etc/nginx/sites-available/pdf-processor
server {
    listen 80;
    server_name your-domain.com;

    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support (for future features)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}

# Enable site
# sudo ln -s /etc/nginx/sites-available/pdf-processor /etc/nginx/sites-enabled/
# sudo nginx -t
# sudo systemctl reload nginx
```

### SSL with Let's Encrypt

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal (add to crontab)
0 12 * * * /usr/bin/certbot renew --quiet
```

---

## Systemd Service

### Create Service File

```ini
# /etc/systemd/system/pdf-processor.service
[Unit]
Description=PDF Processing System
After=network.target

[Service]
Type=exec
User=www-data
Group=www-data
WorkingDirectory=/opt/pdf-processor
Environment=PATH=/opt/pdf-processor/venv/bin
ExecStart=/opt/pdf-processor/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

### Deploy and Manage Service

```bash
# Deploy application
sudo mkdir -p /opt/pdf-processor
sudo cp -r . /opt/pdf-processor/
sudo chown -R www-data:www-data /opt/pdf-processor

# Install dependencies in production
cd /opt/pdf-processor
sudo -u www-data python -m venv venv
sudo -u www-data venv/bin/pip install -r requirements.txt

# Enable and start service
sudo systemctl enable pdf-processor.service
sudo systemctl start pdf-processor.service

# Check status
sudo systemctl status pdf-processor.service

# View logs
sudo journalctl -u pdf-processor.service -f
```

---

## Cloud Deployment

### 1. Heroku Deployment

#### Prepare for Heroku
```bash
# Install Heroku CLI
# Create Procfile
echo "web: uvicorn main:app --host 0.0.0.0 --port \$PORT" > Procfile

# Create runtime.txt
echo "python-3.9.16" > runtime.txt

# Commit changes
git add .
git commit -m "Prepare for Heroku deployment"
```

#### Deploy to Heroku
```bash
# Create Heroku app
heroku create your-pdf-processor-app

# Set environment variables
heroku config:set DATABASE_URL=sqlite:///./pdf_data.db
heroku config:set PDF_FOLDER_PATH=./pdfs

# Deploy
git push heroku main

# Scale up
heroku ps:scale web=1
```

### 2. AWS EC2 Deployment

#### Launch EC2 Instance
```bash
# Connect to instance
ssh -i your-key.pem ubuntu@your-ec2-instance

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install python3 python3-pip python3-venv nginx -y

# Clone and setup application
git clone https://github.com/Raman369AI/pdf-processing-system.git
cd pdf-processing-system
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Setup systemd service (as above)
# Configure nginx (as above)
```

### 3. Google Cloud Platform

#### Using Google Cloud Run
```bash
# Build and push to Container Registry
gcloud builds submit --tag gcr.io/your-project/pdf-processor

# Deploy to Cloud Run
gcloud run deploy pdf-processor \
    --image gcr.io/your-project/pdf-processor \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --memory 1Gi \
    --cpu 1 \
    --port 8000
```

---

## Database Considerations

### SQLite in Production
- **Pros**: Simple, no setup required, good for single-instance deployments
- **Cons**: No concurrent writes, not suitable for multi-instance deployments
- **Recommendation**: Fine for small-scale production, single server

### Upgrading to PostgreSQL
```python
# requirements.txt
asyncpg==0.28.0
alembic==1.12.0

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/dbname")

# Update DatabaseManager to use asyncpg instead of aiosqlite
```

---

## Monitoring and Logging

### Application Logging
```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pdf_processor.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
```

### Health Check Endpoint
```python
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}
```

### Monitoring with Prometheus
```python
# Add to requirements.txt
prometheus-client==0.17.1

# Add metrics endpoint
from prometheus_client import Counter, Histogram, generate_latest

pdf_processed_total = Counter('pdf_processed_total', 'Total PDFs processed')
processing_duration = Histogram('pdf_processing_seconds', 'Time spent processing PDFs')

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

---

## Security Considerations

### Production Security Checklist

- [ ] Use HTTPS (SSL/TLS certificates)
- [ ] Implement rate limiting
- [ ] Add authentication/authorization
- [ ] Validate file uploads (size, type, content)
- [ ] Use environment variables for secrets
- [ ] Keep dependencies updated
- [ ] Implement proper error handling (don't expose stack traces)
- [ ] Use a reverse proxy (nginx/Apache)
- [ ] Regular security updates
- [ ] Monitor access logs

### File Upload Security
```python
import magic

def validate_pdf(file_content: bytes) -> bool:
    """Validate that uploaded file is actually a PDF"""
    mime = magic.from_buffer(file_content, mime=True)
    return mime == 'application/pdf'

# Add to upload endpoint
if not validate_pdf(await file.read()):
    raise HTTPException(status_code=400, detail="Invalid PDF file")
```

---

## Backup and Recovery

### Database Backup
```bash
# SQLite backup
cp pdf_data.db pdf_data_backup_$(date +%Y%m%d_%H%M%S).db

# Automated backup script
#!/bin/bash
BACKUP_DIR="/opt/backups/pdf-processor"
DB_FILE="/opt/pdf-processor/pdf_data.db"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR
cp $DB_FILE "$BACKUP_DIR/pdf_data_$DATE.db"

# Keep only last 30 backups
cd $BACKUP_DIR
ls -t pdf_data_*.db | tail -n +31 | xargs rm -f
```

### Application Backup
```bash
# Backup entire application directory
tar -czf pdf-processor-backup-$(date +%Y%m%d).tar.gz \
    /opt/pdf-processor \
    --exclude='/opt/pdf-processor/venv' \
    --exclude='/opt/pdf-processor/__pycache__'
```

This deployment guide covers various scenarios from development to production. Choose the deployment method that best fits your infrastructure and requirements.