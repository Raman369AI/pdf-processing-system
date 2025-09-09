import os
import asyncio
import re
import uuid
from datetime import datetime
from typing import Dict, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import PyPDF2
import aiosqlite
import uvicorn
from celery import Celery
from models import PDFExtractedData, PendingOrder, PDFDataUpdate, OrderStatus

# Configuration
PDF_FOLDER = "pdfs"
DB_PATH = "pdf_data.db"
REDIS_URL = "redis://localhost:6379/0"

# Celery client configuration
celery_app = Celery('pdf_processor')
celery_app.conf.broker_url = REDIS_URL
celery_app.conf.result_backend = REDIS_URL

class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._lock = asyncio.Lock()
    
    async def init_db(self):
        async with self._lock:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS pdf_extractions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        filename TEXT NOT NULL UNIQUE,
                        invoice_number TEXT,
                        customer_name TEXT,
                        customer_email TEXT,
                        order_date TEXT,
                        due_date TEXT,
                        total_amount REAL,
                        tax_amount REAL,
                        currency TEXT,
                        items_description TEXT,
                        quantity INTEGER,
                        unit_price REAL,
                        billing_address TEXT,
                        shipping_address TEXT,
                        vendor_name TEXT,
                        payment_terms TEXT,
                        notes TEXT,
                        content_preview TEXT,
                        date_extracted TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS pending_orders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        filename TEXT NOT NULL,
                        pdf_data TEXT NOT NULL,
                        status TEXT DEFAULT 'pending',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                await db.commit()
    
    async def insert_pdf_data(self, data: PDFExtractedData):
        async with self._lock:
            async with aiosqlite.connect(self.db_path) as db:
                try:
                    await db.execute('''
                        INSERT OR REPLACE INTO pdf_extractions 
                        (filename, invoice_number, customer_name, customer_email, order_date, due_date,
                         total_amount, tax_amount, currency, items_description, quantity, unit_price,
                         billing_address, shipping_address, vendor_name, payment_terms, notes,
                         content_preview, date_extracted)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (data.filename, data.invoice_number, data.customer_name, data.customer_email,
                         data.order_date, data.due_date, data.total_amount, data.tax_amount, data.currency,
                         data.items_description, data.quantity, data.unit_price, data.billing_address,
                         data.shipping_address, data.vendor_name, data.payment_terms, data.notes,
                         data.content_preview, data.date_extracted.isoformat()))
                    await db.commit()
                    return True
                except Exception as e:
                    print(f"Database error: {e}")
                    return False
    
    async def get_all_records(self):
        async with self._lock:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute('SELECT * FROM pdf_extractions ORDER BY created_at DESC') as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
    
    async def insert_pending_order(self, pdf_data: PDFExtractedData):
        async with self._lock:
            async with aiosqlite.connect(self.db_path) as db:
                try:
                    await db.execute('''
                        INSERT INTO pending_orders (filename, pdf_data, status)
                        VALUES (?, ?, ?)
                    ''', (pdf_data.filename, pdf_data.json(), OrderStatus.PENDING))
                    await db.commit()
                    return True
                except Exception as e:
                    print(f"Pending order error: {e}")
                    return False
    
    async def get_pending_orders(self):
        async with self._lock:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute('SELECT * FROM pending_orders WHERE status = ? ORDER BY created_at DESC', 
                                    (OrderStatus.PENDING,)) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
    
    async def update_pending_order(self, order_id: int, pdf_data: PDFExtractedData):
        async with self._lock:
            async with aiosqlite.connect(self.db_path) as db:
                try:
                    await db.execute('''
                        UPDATE pending_orders 
                        SET pdf_data = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (pdf_data.json(), order_id))
                    await db.commit()
                    return True
                except Exception as e:
                    print(f"Update pending order error: {e}")
                    return False
    
    async def get_pending_count(self):
        async with self._lock:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute('SELECT COUNT(*) FROM pending_orders WHERE status = ?', 
                                    (OrderStatus.PENDING,)) as cursor:
                    result = await cursor.fetchone()
                    return result[0] if result else 0

db_manager = DatabaseManager(DB_PATH)


def extract_pdf_fields(text: str, filename: str) -> PDFExtractedData:
    """Common field extraction logic"""
    content_preview = text[:200] if text else "No content extracted"
    
    # Mock field extraction (in production, use proper parsing)
    invoice_match = re.search(r'invoice[#\s]+([A-Z0-9-]+)', text, re.IGNORECASE)
    total_match = re.search(r'total[:\s]*\$?([0-9,]+\.?[0-9]*)', text, re.IGNORECASE)
    email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', text)
    date_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', text)
    
    return PDFExtractedData(
        filename=filename,
        invoice_number=invoice_match.group(1) if invoice_match else None,
        customer_name=None,  # Would need more sophisticated parsing
        customer_email=email_match.group(1) if email_match else None,
        order_date=date_match.group(1) if date_match else None,
        due_date=None,
        total_amount=float(total_match.group(1).replace(',', '')) if total_match else None,
        tax_amount=None,
        currency="USD",
        items_description=None,
        quantity=None,
        unit_price=None,
        billing_address=None,
        shipping_address=None,
        vendor_name=None,
        payment_terms=None,
        notes=None,
        content_preview=content_preview,
        full_text=text,
        date_extracted=datetime.now()
    )

def extract_pdf_data(file_path: str) -> PDFExtractedData:
    """Enhanced PDF data extraction with field parsing from file path"""
    try:
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            
            filename = os.path.basename(file_path)
            return extract_pdf_fields(text, filename)
            
    except Exception as e:
        return PDFExtractedData(
            filename=os.path.basename(file_path),
            content_preview=f'Error processing PDF: {str(e)}',
            full_text='',
            date_extracted=datetime.now()
        )

def extract_pdf_from_bytes(content: bytes, filename: str) -> PDFExtractedData:
    """Extract PDF data from bytes content (for uploads)"""
    try:
        from io import BytesIO
        reader = PyPDF2.PdfReader(BytesIO(content))
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        
        return extract_pdf_fields(text, filename)
        
    except Exception as e:
        return PDFExtractedData(
            filename=filename,
            content_preview=f'Error processing uploaded PDF: {str(e)}',
            full_text='',
            date_extracted=datetime.now()
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup - only initialize database
    await db_manager.init_db()
    
    yield
    
    # Shutdown - nothing to clean up

app = FastAPI(title="PDF Processing System", lifespan=lifespan)
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    pending_count = await db_manager.get_pending_count()
    # Get processed PDFs from database instead of in-memory storage
    records = await db_manager.get_all_records()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "processed_pdfs": {record['filename']: record for record in records},
        "pending_count": pending_count
    })

@app.get("/api/model-schema")
async def get_model_schema():
    """Return Pydantic model schema for dynamic form generation"""
    schema = PDFExtractedData.model_json_schema()
    
    # Extract field information
    fields = {}
    properties = schema.get('properties', {})
    
    for field_name, field_info in properties.items():
        # Skip system fields
        if field_name in ['filename', 'content_preview', 'full_text', 'date_extracted']:
            continue
            
        field_type = field_info.get('type', 'string')
        field_description = field_info.get('description', '')
        field_default = field_info.get('default')
        
        # Handle anyOf for optional fields
        if 'anyOf' in field_info:
            for option in field_info['anyOf']:
                if option.get('type') != 'null':
                    field_type = option.get('type', 'string')
                    break
        
        fields[field_name] = {
            'type': field_type,
            'description': field_description,
            'default': field_default,
            'required': field_name in schema.get('required', [])
        }
    
    return {'fields': fields}

@app.get("/api/pdfs")
async def get_processed_pdfs():
    records = await db_manager.get_all_records()
    return {"pdfs": records}

@app.post("/api/commit/{filename}")
async def commit_to_database(filename: str):
    # With Celery, PDFs are automatically committed to database
    # This endpoint can now just confirm the PDF exists in database
    records = await db_manager.get_all_records()
    pdf_record = next((record for record in records if record['filename'] == filename), None)
    
    if pdf_record:
        return {"message": "PDF already committed to database"}
    else:
        return {"error": "PDF not found in database"}

@app.post("/api/pending/{filename}")
async def send_to_pending(filename: str):
    # Find PDF in database records
    records = await db_manager.get_all_records()
    pdf_record = next((record for record in records if record['filename'] == filename), None)
    
    if not pdf_record:
        return {"error": "PDF not found"}
    
    # Convert database record back to PDFExtractedData
    pdf_data = PDFExtractedData(
        filename=pdf_record['filename'],
        invoice_number=pdf_record.get('invoice_number'),
        customer_name=pdf_record.get('customer_name'),
        customer_email=pdf_record.get('customer_email'),
        order_date=pdf_record.get('order_date'),
        due_date=pdf_record.get('due_date'),
        total_amount=pdf_record.get('total_amount'),
        tax_amount=pdf_record.get('tax_amount'),
        currency=pdf_record.get('currency'),
        items_description=pdf_record.get('items_description'),
        quantity=pdf_record.get('quantity'),
        unit_price=pdf_record.get('unit_price'),
        billing_address=pdf_record.get('billing_address'),
        shipping_address=pdf_record.get('shipping_address'),
        vendor_name=pdf_record.get('vendor_name'),
        payment_terms=pdf_record.get('payment_terms'),
        notes=pdf_record.get('notes'),
        content_preview=pdf_record.get('content_preview'),
        full_text=pdf_record.get('content_preview', ''),  # Use content_preview as fallback
        date_extracted=datetime.fromisoformat(pdf_record.get('date_extracted', datetime.now().isoformat()))
    )
    
    success = await db_manager.insert_pending_order(pdf_data)
    
    if success:
        return {"message": "Order sent to pending successfully"}
    else:
        return {"error": "Failed to send order to pending"}

@app.get("/api/pending")
async def get_pending_orders():
    orders = await db_manager.get_pending_orders()
    return {"orders": orders}

@app.get("/api/pending/count")
async def get_pending_count():
    count = await db_manager.get_pending_count()
    return {"count": count}

@app.put("/api/pending/{order_id}")
async def update_pending_order(order_id: int, update_data: dict):
    # Get current pending order
    orders = await db_manager.get_pending_orders()
    current_order = None
    for order in orders:
        if order['id'] == order_id:
            current_order = order
            break
    
    if not current_order:
        raise HTTPException(status_code=404, detail="Pending order not found")
    
    # Parse current PDF data and update with new values
    import json
    pdf_data_dict = json.loads(current_order['pdf_data'])
    
    # Update fields that are provided
    for key, value in update_data.items():
        if key in pdf_data_dict and value is not None:
            pdf_data_dict[key] = value
    
    # Create updated PDFExtractedData
    updated_pdf_data = PDFExtractedData(**pdf_data_dict)
    
    success = await db_manager.update_pending_order(order_id, updated_pdf_data)
    
    if success:
        return {"message": "Pending order updated successfully"}
    else:
        return {"error": "Failed to update pending order"}

@app.get("/api/database")
async def get_database_records():
    records = await db_manager.get_all_records()
    return {"records": records}

@app.post("/api/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    """Upload PDF and submit to Celery for processing"""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    try:
        # Read file content
        content = await file.read()
        
        # Submit to Celery for processing
        task = celery_app.send_task('process_pdf_bytes', args=[content, file.filename])
        
        return {
            "message": "PDF uploaded and submitted for processing",
            "filename": file.filename,
            "task_id": task.id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")

@app.post("/api/upload-pdf-to-folder")
async def upload_pdf_to_folder(file: UploadFile = File(...)):
    """Upload PDF to monitored folder for automatic processing"""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    try:
        # Ensure PDF folder exists
        os.makedirs(PDF_FOLDER, exist_ok=True)
        
        # Generate unique filename to avoid conflicts
        unique_filename = f"{uuid.uuid4().hex}_{file.filename}"
        file_path = os.path.join(PDF_FOLDER, unique_filename)
        
        # Save file to monitored folder
        content = await file.read()
        with open(file_path, 'wb') as f:
            f.write(content)
        
        return {
            "message": "PDF uploaded to monitored folder for automatic processing",
            "filename": file.filename,
            "unique_filename": unique_filename,
            "file_path": file_path,
            "monitoring_info": "File will be automatically detected and processed by pdf_monitor.py"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving PDF to folder: {str(e)}")

@app.get("/api/task-status/{task_id}")
async def get_task_status(task_id: str):
    """Get the status of a Celery task"""
    try:
        result = celery_app.AsyncResult(task_id)
        
        if result.state == 'PENDING':
            response = {
                'state': result.state,
                'status': 'Task is waiting to be processed'
            }
        elif result.state == 'PROGRESS':
            response = {
                'state': result.state,
                'status': result.info.get('status', 'Processing...'),
                'current': result.info.get('current', 0),
                'total': result.info.get('total', 1)
            }
        elif result.state == 'SUCCESS':
            response = {
                'state': result.state,
                'status': 'Task completed successfully',
                'result': result.result
            }
        else:
            # Task failed
            response = {
                'state': result.state,
                'status': str(result.info),
                'error': True
            }
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting task status: {str(e)}")

@app.get("/api/processing-status/{filename}")
async def get_processing_status(filename: str):
    """Check if a PDF has been processed and get its status"""
    try:
        # Check if file exists in database
        records = await db_manager.get_all_records()
        pdf_record = next((record for record in records if record['filename'] == filename), None)
        
        if pdf_record:
            return {
                "status": "completed",
                "filename": filename,
                "processed": True,
                "data": pdf_record,
                "message": "PDF has been processed and stored in database"
            }
        else:
            # Check if file exists in pending
            pending = await db_manager.get_pending_orders()
            pending_record = next((order for order in pending if filename in order['pdf_data']), None)
            
            if pending_record:
                return {
                    "status": "pending",
                    "filename": filename,
                    "processed": True,
                    "message": "PDF has been processed and is in pending orders"
                }
            else:
                # Check if file exists in folder (being processed or waiting)
                file_path = os.path.join(PDF_FOLDER, filename)
                unique_files = [f for f in os.listdir(PDF_FOLDER) if filename in f] if os.path.exists(PDF_FOLDER) else []
                
                if os.path.exists(file_path) or unique_files:
                    return {
                        "status": "processing",
                        "filename": filename,
                        "processed": False,
                        "message": "PDF is being processed or waiting in queue"
                    }
                else:
                    return {
                        "status": "not_found",
                        "filename": filename,
                        "processed": False,
                        "message": "PDF not found in system"
                    }
                    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking processing status: {str(e)}")

@app.put("/api/pdfs/{filename}")
async def update_pdf_data(filename: str, update_data: dict):
    # Find PDF in database records
    records = await db_manager.get_all_records()
    pdf_record = next((record for record in records if record['filename'] == filename), None)
    
    if not pdf_record:
        raise HTTPException(status_code=404, detail="PDF not found")
    
    # Convert to dict for updating
    current_dict = dict(pdf_record)
    
    # Update fields that are provided
    for key, value in update_data.items():
        if key in current_dict and value is not None:
            current_dict[key] = value
    
    # Create updated PDFExtractedData and save to database
    updated_data = PDFExtractedData(
        filename=current_dict['filename'],
        invoice_number=current_dict.get('invoice_number'),
        customer_name=current_dict.get('customer_name'),
        customer_email=current_dict.get('customer_email'),
        order_date=current_dict.get('order_date'),
        due_date=current_dict.get('due_date'),
        total_amount=current_dict.get('total_amount'),
        tax_amount=current_dict.get('tax_amount'),
        currency=current_dict.get('currency'),
        items_description=current_dict.get('items_description'),
        quantity=current_dict.get('quantity'),
        unit_price=current_dict.get('unit_price'),
        billing_address=current_dict.get('billing_address'),
        shipping_address=current_dict.get('shipping_address'),
        vendor_name=current_dict.get('vendor_name'),
        payment_terms=current_dict.get('payment_terms'),
        notes=current_dict.get('notes'),
        content_preview=current_dict.get('content_preview'),
        full_text=current_dict.get('content_preview', ''),
        date_extracted=datetime.fromisoformat(current_dict.get('date_extracted', datetime.now().isoformat()))
    )
    
    success = await db_manager.insert_pdf_data(updated_data)
    
    if success:
        return {"message": "PDF data updated successfully", "data": updated_data.model_dump()}
    else:
        raise HTTPException(status_code=500, detail="Failed to update PDF data")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)