import os
import asyncio
import threading
import re
import uuid
from pathlib import Path
from datetime import datetime
from queue import Queue
from typing import Dict, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import PyPDF2
import aiosqlite
import uvicorn
from models import PDFExtractedData, PendingOrder, PDFDataUpdate, OrderStatus

# Simple in-memory storage and queue
pdf_queue = Queue()
processed_pdfs = {}
PDF_FOLDER = "pdfs"
DB_PATH = "pdf_data.db"

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

class PDFHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_file and event.src_path.endswith('.pdf'):
            pdf_queue.put(event.src_path)

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

def pdf_processor():
    """Background thread to process PDF queue"""
    while True:
        try:
            file_path = pdf_queue.get(timeout=1)
            data = extract_pdf_data(file_path)
            processed_pdfs[data.filename] = data
            pdf_queue.task_done()
        except:
            continue

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await db_manager.init_db()
    
    # Start PDF monitoring
    event_handler = PDFHandler()
    observer = Observer()
    observer.schedule(event_handler, PDF_FOLDER, recursive=False)
    observer.start()
    
    # Start background processor
    processor_thread = threading.Thread(target=pdf_processor, daemon=True)
    processor_thread.start()
    
    # Process existing PDFs
    if os.path.exists(PDF_FOLDER):
        for filename in os.listdir(PDF_FOLDER):
            if filename.endswith('.pdf'):
                pdf_queue.put(os.path.join(PDF_FOLDER, filename))
    
    yield
    
    # Shutdown
    observer.stop()
    observer.join()

app = FastAPI(title="PDF Processing System", lifespan=lifespan)
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    pending_count = await db_manager.get_pending_count()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "processed_pdfs": processed_pdfs,
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
    return {"pdfs": [pdf.dict() for pdf in processed_pdfs.values()]}

@app.post("/api/commit/{filename}")
async def commit_to_database(filename: str):
    if filename not in processed_pdfs:
        return {"error": "PDF not found"}
    
    data = processed_pdfs[filename]
    success = await db_manager.insert_pdf_data(data)
    
    if success:
        return {"message": "Data committed to database successfully"}
    else:
        return {"error": "Failed to commit data to database"}

@app.post("/api/pending/{filename}")
async def send_to_pending(filename: str):
    if filename not in processed_pdfs:
        return {"error": "PDF not found"}
    
    data = processed_pdfs[filename]
    success = await db_manager.insert_pending_order(data)
    
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
    """Upload PDF directly without affecting the queue system"""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    try:
        # Generate unique filename to avoid conflicts
        unique_filename = f"{uuid.uuid4().hex}_{file.filename}"
        
        # Read file content
        content = await file.read()
        
        # Process PDF directly without saving to disk
        pdf_data = extract_pdf_from_bytes(content, file.filename)
        
        # Add to processed_pdfs with original filename for user display
        processed_pdfs[file.filename] = pdf_data
        
        return {
            "message": "PDF uploaded and processed successfully",
            "filename": file.filename,
            "data": pdf_data.dict()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")

@app.put("/api/pdfs/{filename}")
async def update_pdf_data(filename: str, update_data: dict):
    if filename not in processed_pdfs:
        raise HTTPException(status_code=404, detail="PDF not found")
    
    current_data = processed_pdfs[filename]
    current_dict = current_data.dict()
    
    # Update fields that are provided
    for key, value in update_data.items():
        if key in current_dict and value is not None:
            current_dict[key] = value
    
    # Create updated PDFExtractedData
    updated_data = PDFExtractedData(**current_dict)
    processed_pdfs[filename] = updated_data
    
    return {"message": "PDF data updated successfully", "data": updated_data.dict()}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)