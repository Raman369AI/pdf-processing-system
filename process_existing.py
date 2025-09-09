#!/usr/bin/env python3
"""
Utility script to process existing PDFs in the folder
Can be run manually or as part of deployment process
"""
import os
import sys
import logging
from celery import Celery

# Configuration
PDF_FOLDER = "pdfs"
REDIS_URL = "redis://localhost:6379/0"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Celery client configuration
celery_app = Celery('pdf_processor')
celery_app.conf.broker_url = REDIS_URL
celery_app.conf.result_backend = REDIS_URL

def process_existing_pdfs():
    """Process any existing PDFs in the folder"""
    if not os.path.exists(PDF_FOLDER):
        logger.info(f"PDF folder '{PDF_FOLDER}' does not exist, creating it...")
        os.makedirs(PDF_FOLDER)
        logger.info("No existing PDFs to process")
        return 0
    
    pdf_files = [f for f in os.listdir(PDF_FOLDER) if f.endswith('.pdf')]
    
    if not pdf_files:
        logger.info("No existing PDFs found")
        return 0
    
    logger.info(f"Found {len(pdf_files)} existing PDFs, submitting for processing...")
    
    submitted_count = 0
    failed_count = 0
    
    for filename in pdf_files:
        file_path = os.path.join(PDF_FOLDER, filename)
        try:
            task = celery_app.send_task('process_pdf', args=[file_path])
            logger.info(f"Submitted task {task.id} for existing PDF: {filename}")
            submitted_count += 1
        except Exception as e:
            logger.error(f"Failed to submit task for existing PDF {filename}: {e}")
            failed_count += 1
    
    logger.info(f"Processing complete: {submitted_count} submitted, {failed_count} failed")
    return submitted_count

def check_celery_connection():
    """Check if Celery broker is available"""
    try:
        # Try to get worker stats to test connection
        inspect = celery_app.control.inspect()
        stats = inspect.stats()
        if stats:
            logger.info("Celery connection successful")
            return True
        else:
            logger.warning("No Celery workers found, but broker connection successful")
            return True
    except Exception as e:
        logger.error(f"Failed to connect to Celery broker: {e}")
        logger.error("Make sure Redis is running and Celery workers are started")
        return False

def main():
    """Main function"""
    logger.info("Starting existing PDF processing utility")
    
    # Check Celery connection
    if not check_celery_connection():
        logger.error("Cannot connect to Celery broker. Exiting.")
        sys.exit(1)
    
    # Process existing PDFs
    submitted_count = process_existing_pdfs()
    
    if submitted_count > 0:
        logger.info(f"Successfully submitted {submitted_count} PDFs for processing")
        logger.info("Monitor worker logs to see processing progress")
    
    logger.info("Existing PDF processing utility completed")

if __name__ == '__main__':
    main()