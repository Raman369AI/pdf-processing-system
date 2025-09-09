#!/usr/bin/env python3
"""
Standalone PDF monitoring service
Watches the PDF folder and submits processing tasks to Celery
"""
import os
import sys
import time
import logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
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

class PDFHandler(FileSystemEventHandler):
    """Handle PDF file system events"""
    
    def on_created(self, event):
        """Handle file creation events"""
        if event.is_file and event.src_path.endswith('.pdf'):
            logger.info(f"New PDF detected: {event.src_path}")
            try:
                # Submit PDF processing task to Celery
                task = celery_app.send_task('process_pdf', args=[event.src_path])
                logger.info(f"Submitted task {task.id} for {event.src_path}")
            except Exception as e:
                logger.error(f"Failed to submit task for {event.src_path}: {e}")
    
    def on_moved(self, event):
        """Handle file move events (in case files are moved into the folder)"""
        if event.is_file and event.dest_path.endswith('.pdf'):
            logger.info(f"PDF moved to folder: {event.dest_path}")
            try:
                task = celery_app.send_task('process_pdf', args=[event.dest_path])
                logger.info(f"Submitted task {task.id} for moved file {event.dest_path}")
            except Exception as e:
                logger.error(f"Failed to submit task for moved file {event.dest_path}: {e}")

def ensure_pdf_folder():
    """Ensure PDF folder exists"""
    if not os.path.exists(PDF_FOLDER):
        os.makedirs(PDF_FOLDER)
        logger.info(f"Created PDF folder: {PDF_FOLDER}")

def process_existing_pdfs():
    """Process any existing PDFs in the folder on startup"""
    if not os.path.exists(PDF_FOLDER):
        logger.info("PDF folder does not exist, skipping existing PDF processing")
        return
    
    pdf_files = [f for f in os.listdir(PDF_FOLDER) if f.endswith('.pdf')]
    
    if not pdf_files:
        logger.info("No existing PDFs found")
        return
    
    logger.info(f"Found {len(pdf_files)} existing PDFs, submitting for processing...")
    
    for filename in pdf_files:
        file_path = os.path.join(PDF_FOLDER, filename)
        try:
            task = celery_app.send_task('process_pdf', args=[file_path])
            logger.info(f"Submitted task {task.id} for existing PDF: {filename}")
        except Exception as e:
            logger.error(f"Failed to submit task for existing PDF {filename}: {e}")

def main():
    """Main monitoring loop"""
    logger.info("Starting PDF Monitor Service")
    
    # Ensure folder exists
    ensure_pdf_folder()
    
    # Process existing PDFs
    process_existing_pdfs()
    
    # Set up file watcher
    event_handler = PDFHandler()
    observer = Observer()
    observer.schedule(event_handler, PDF_FOLDER, recursive=False)
    
    try:
        observer.start()
        logger.info(f"Started monitoring {PDF_FOLDER} for new PDFs...")
        
        # Keep the service running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        observer.stop()
        observer.join()
        logger.info("PDF Monitor Service stopped")

if __name__ == '__main__':
    main()