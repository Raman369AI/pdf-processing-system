import os
import asyncio
import logging
from datetime import datetime
from celery import Celery
import aiosqlite
from models import PDFExtractedData
from main import DatabaseManager, DB_PATH
from pdf_processor import extract_pdf_from_file, extract_pdf_from_bytes

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Celery configuration
REDIS_URL = 'redis://localhost:6379/0'
app = Celery('pdf_processor')
app.conf.broker_url = REDIS_URL
app.conf.result_backend = REDIS_URL

# Celery configuration
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_default_retry_delay=60,
    task_max_retries=3,
    worker_log_format='[%(asctime)s: %(levelname)s/%(processName)s] %(message)s',
    worker_task_log_format='[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s',
)


@app.task(bind=True, name='process_pdf')
def process_pdf_task(self, file_path: str):
    """
    Celery task to process PDF files from file system
    """
    filename = os.path.basename(file_path)
    logger.info(f"Processing PDF: {filename}")
    
    try:
        # Check if file exists
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Use the configurable PDF processor
        pdf_data = extract_pdf_from_file(file_path, PDFExtractedData)
        logger.info(f"Extracted data from {filename}")
        
        # Store in database using async context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def store_data():
            db_manager = DatabaseManager(DB_PATH)
            await db_manager.init_db()
            success = await db_manager.insert_pdf_data(pdf_data)
            return success
        
        try:
            success = loop.run_until_complete(store_data())
        finally:
            loop.close()
        
        if success:
            logger.info(f"Successfully processed and stored: {filename}")
            return {
                'status': 'success',
                'filename': filename,
                'message': f'Successfully processed {filename}'
            }
        else:
            raise Exception('Failed to store PDF data in database')
            
    except Exception as e:
        logger.error(f"Error processing {filename}: {str(e)}")
        # Retry the task if it fails
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying {filename} (attempt {self.request.retries + 1})")
            raise self.retry(countdown=60, exc=e)
        else:
            logger.error(f"Max retries exceeded for {filename}")
            raise

@app.task(bind=True, name='process_pdf_bytes')
def process_pdf_bytes_task(self, content_bytes: bytes, filename: str):
    """
    Celery task to process PDF files from bytes (for uploads)
    """
    logger.info(f"Processing uploaded PDF: {filename}")
    
    try:
        # Use the configurable PDF processor
        pdf_data = extract_pdf_from_bytes(content_bytes, filename, PDFExtractedData)
        logger.info(f"Extracted data from uploaded {filename}")
        
        # Store in database using async context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def store_data():
            db_manager = DatabaseManager(DB_PATH)
            await db_manager.init_db()
            success = await db_manager.insert_pdf_data(pdf_data)
            return success
        
        try:
            success = loop.run_until_complete(store_data())
        finally:
            loop.close()
        
        if success:
            logger.info(f"Successfully processed and stored uploaded: {filename}")
            return {
                'status': 'success',
                'filename': filename,
                'message': f'Successfully processed uploaded {filename}'
            }
        else:
            raise Exception('Failed to store PDF data in database')
            
    except Exception as e:
        logger.error(f"Error processing uploaded {filename}: {str(e)}")
        # Retry the task if it fails
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying uploaded {filename} (attempt {self.request.retries + 1})")
            raise self.retry(countdown=60, exc=e)
        else:
            logger.error(f"Max retries exceeded for uploaded {filename}")
            raise

if __name__ == '__main__':
    app.start()