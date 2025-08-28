# Customization Guide

## Overview

The PDF Processing System is designed to be highly customizable. This guide covers how to modify the system to meet your specific requirements.

## Data Model Customization

### Adding New Fields

The system uses Pydantic models for data validation and automatic form generation. Adding new fields is straightforward:

#### 1. Update the Pydantic Model

Edit `models.py`:

```python
class PDFExtractedData(BaseModel):
    # Existing fields...
    
    # Add your new fields
    purchase_order: Optional[str] = Field(None, description="Purchase order number")
    department: Optional[str] = Field(None, description="Department or cost center")
    project_code: Optional[str] = Field(None, description="Project code")
    approval_status: Optional[str] = Field("pending", description="Approval status")
    priority_level: Optional[int] = Field(1, description="Priority level (1-5)")
    
    # Custom validation
    @validator('priority_level')
    def validate_priority(cls, v):
        if v is not None and (v < 1 or v > 5):
            raise ValueError('Priority level must be between 1 and 5')
        return v
```

#### 2. Update Database Schema

The system automatically handles new columns, but for explicit control, update the `DatabaseManager.init_db()` method:

```python
async def init_db(self):
    async with self._lock:
        async with aiosqlite.connect(self.db_path) as db:
            # Add new columns to existing table
            try:
                await db.execute('ALTER TABLE pdf_extractions ADD COLUMN purchase_order TEXT')
                await db.execute('ALTER TABLE pdf_extractions ADD COLUMN department TEXT')
                await db.execute('ALTER TABLE pdf_extractions ADD COLUMN project_code TEXT')
                await db.execute('ALTER TABLE pdf_extractions ADD COLUMN approval_status TEXT DEFAULT "pending"')
                await db.execute('ALTER TABLE pdf_extractions ADD COLUMN priority_level INTEGER DEFAULT 1')
            except Exception as e:
                # Columns might already exist
                pass
            await db.commit()
```

#### 3. Update Extraction Logic

Modify `extract_pdf_fields()` in `main.py` to extract your new fields:

```python
def extract_pdf_fields(text: str, filename: str) -> PDFExtractedData:
    # Existing extraction logic...
    
    # Add custom extraction patterns
    po_match = re.search(r'P\.?O\.?\s*(?:number)?[:\s]+([A-Z0-9-]+)', text, re.IGNORECASE)
    dept_match = re.search(r'department[:\s]+([A-Za-z\s]+)', text, re.IGNORECASE)
    project_match = re.search(r'project[:\s]+([A-Z0-9-]+)', text, re.IGNORECASE)
    
    return PDFExtractedData(
        # Existing fields...
        
        # New fields
        purchase_order=po_match.group(1) if po_match else None,
        department=dept_match.group(1).strip() if dept_match else None,
        project_code=project_match.group(1) if project_match else None,
        approval_status="pending",  # Default value
        priority_level=1,  # Default priority
        
        # Rest of existing fields...
    )
```

#### 4. Frontend Automatically Adapts

The frontend will automatically generate form fields for your new data! The system reads the Pydantic model schema and creates appropriate input fields.

---

## Custom PDF Processing

### Advanced Text Extraction

Replace basic regex patterns with more sophisticated extraction:

```python
import spacy
from typing import Dict, Any

# Load spaCy model (install with: python -m spacy download en_core_web_sm)
nlp = spacy.load("en_core_web_sm")

def advanced_extract_fields(text: str, filename: str) -> PDFExtractedData:
    """Advanced field extraction using NLP"""
    doc = nlp(text)
    
    # Extract entities
    entities = {}
    for ent in doc.ents:
        if ent.label_ == "MONEY":
            entities['amount'] = extract_amount(ent.text)
        elif ent.label_ == "PERSON":
            entities['customer_name'] = ent.text
        elif ent.label_ == "ORG":
            entities['vendor_name'] = ent.text
    
    # Custom patterns for specific formats
    invoice_patterns = [
        r'invoice\s*(?:number|#)?:?\s*([A-Z0-9-]+)',
        r'bill\s*(?:number|#)?:?\s*([A-Z0-9-]+)',
        r'reference\s*(?:number|#)?:?\s*([A-Z0-9-]+)'
    ]
    
    invoice_number = None
    for pattern in invoice_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            invoice_number = match.group(1)
            break
    
    return PDFExtractedData(
        filename=filename,
        invoice_number=invoice_number,
        customer_name=entities.get('customer_name'),
        vendor_name=entities.get('vendor_name'),
        total_amount=entities.get('amount'),
        # ... other fields
    )
```

### Machine Learning Integration

Integrate ML models for better extraction:

```python
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer

# Load pre-trained models (you'd train these first)
# invoice_classifier = joblib.load('models/invoice_classifier.pkl')
# amount_extractor = joblib.load('models/amount_extractor.pkl')

def ml_extract_fields(text: str, filename: str) -> PDFExtractedData:
    """ML-powered field extraction"""
    
    # Classify document type
    # doc_type = invoice_classifier.predict([text])[0]
    
    # Extract specific fields based on document type
    if doc_type == 'invoice':
        return extract_invoice_fields(text, filename)
    elif doc_type == 'receipt':
        return extract_receipt_fields(text, filename)
    else:
        return extract_generic_fields(text, filename)
```

---

## User Interface Customization

### Custom CSS Styling

Modify the appearance by updating the CSS in `templates/index.html`:

```css
/* Add to the <style> section */

/* Custom color scheme */
:root {
    --primary-color: #2563eb;
    --secondary-color: #64748b;
    --success-color: #10b981;
    --warning-color: #f59e0b;
    --danger-color: #ef4444;
    --background-color: #f8fafc;
}

/* Dark mode support */
@media (prefers-color-scheme: dark) {
    :root {
        --background-color: #1e293b;
        --text-color: #f1f5f9;
    }
    
    body {
        background-color: var(--background-color);
        color: var(--text-color);
    }
    
    .section {
        background: #334155;
        color: var(--text-color);
    }
}

/* Custom animations */
.fade-in {
    animation: fadeIn 0.5s ease-in;
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}

/* Custom field styling */
.field-group.priority {
    border-left: 3px solid var(--warning-color);
    padding-left: 15px;
}

.field-group.required label::after {
    content: " *";
    color: var(--danger-color);
}
```

### Custom JavaScript Behavior

Add custom functionality to the frontend:

```javascript
// Add to the <script> section

// Custom field validation
function validateCustomFields(pdf) {
    const errors = [];
    
    if (pdf.total_amount && pdf.total_amount < 0) {
        errors.push('Total amount cannot be negative');
    }
    
    if (pdf.priority_level && (pdf.priority_level < 1 || pdf.priority_level > 5)) {
        errors.push('Priority level must be between 1 and 5');
    }
    
    return errors;
}

// Custom field formatting
function formatCurrency(amount, currency = 'USD') {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: currency
    }).format(amount);
}

// Auto-save functionality
let autoSaveTimeout;
function autoSave(filename, field, value) {
    clearTimeout(autoSaveTimeout);
    autoSaveTimeout = setTimeout(() => {
        updateField(filename, field, value);
        showNotification('Auto-saved', 'success');
    }, 2000); // Auto-save after 2 seconds of inactivity
}

// Custom notifications
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.classList.add('fade-out');
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}
```

---

## Workflow Customization

### Custom Processing Workflow

Create custom workflows for different document types:

```python
from enum import Enum
from typing import Callable

class WorkflowStatus(str, Enum):
    RECEIVED = "received"
    PROCESSING = "processing"
    REVIEW_REQUIRED = "review_required"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"

class CustomWorkflow:
    def __init__(self):
        self.workflows = {
            'invoice': self.invoice_workflow,
            'receipt': self.receipt_workflow,
            'contract': self.contract_workflow
        }
    
    def process_document(self, pdf_data: PDFExtractedData) -> WorkflowStatus:
        doc_type = self.classify_document(pdf_data)
        workflow = self.workflows.get(doc_type, self.default_workflow)
        return workflow(pdf_data)
    
    def invoice_workflow(self, pdf_data: PDFExtractedData) -> WorkflowStatus:
        # Custom invoice processing logic
        if pdf_data.total_amount and pdf_data.total_amount > 10000:
            return WorkflowStatus.REVIEW_REQUIRED
        elif pdf_data.total_amount and pdf_data.customer_name:
            return WorkflowStatus.APPROVED
        else:
            return WorkflowStatus.REVIEW_REQUIRED
    
    def receipt_workflow(self, pdf_data: PDFExtractedData) -> WorkflowStatus:
        # Simple receipt processing
        return WorkflowStatus.APPROVED
    
    def contract_workflow(self, pdf_data: PDFExtractedData) -> WorkflowStatus:
        # Contracts always require review
        return WorkflowStatus.REVIEW_REQUIRED
```

### Email Notifications

Add email notifications for different events:

```python
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class NotificationService:
    def __init__(self, smtp_server: str, smtp_port: int, username: str, password: str):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
    
    def send_notification(self, to_email: str, subject: str, message: str):
        msg = MIMEMultipart()
        msg['From'] = self.username
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(message, 'plain'))
        
        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            server.starttls()
            server.login(self.username, self.password)
            server.send_message(msg)
    
    def notify_high_value_invoice(self, pdf_data: PDFExtractedData):
        if pdf_data.total_amount and pdf_data.total_amount > 10000:
            message = f"""
            High-value invoice detected:
            
            Filename: {pdf_data.filename}
            Invoice Number: {pdf_data.invoice_number}
            Customer: {pdf_data.customer_name}
            Amount: ${pdf_data.total_amount}
            
            Please review and approve.
            """
            
            self.send_notification(
                "manager@company.com",
                f"High-Value Invoice: {pdf_data.invoice_number}",
                message
            )

# Add to main.py
notification_service = NotificationService(
    smtp_server=os.getenv('SMTP_SERVER'),
    smtp_port=int(os.getenv('SMTP_PORT', 587)),
    username=os.getenv('SMTP_USERNAME'),
    password=os.getenv('SMTP_PASSWORD')
)

# Use in PDF processing
def process_with_notifications(pdf_data: PDFExtractedData):
    processed_pdfs[pdf_data.filename] = pdf_data
    notification_service.notify_high_value_invoice(pdf_data)
```

---

## Database Customization

### Custom Queries

Add custom database queries for specific needs:

```python
class CustomDatabaseManager(DatabaseManager):
    async def get_invoices_by_date_range(self, start_date: str, end_date: str):
        async with self._lock:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute('''
                    SELECT * FROM pdf_extractions 
                    WHERE order_date BETWEEN ? AND ?
                    ORDER BY order_date DESC
                ''', (start_date, end_date)) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
    
    async def get_high_value_pending(self, min_amount: float = 5000):
        async with self._lock:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute('''
                    SELECT * FROM pending_orders 
                    WHERE JSON_EXTRACT(pdf_data, '$.total_amount') > ?
                    ORDER BY created_at DESC
                ''', (min_amount,)) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
    
    async def get_summary_stats(self):
        async with self._lock:
            async with aiosqlite.connect(self.db_path) as db:
                stats = {}
                
                # Total processed PDFs
                async with db.execute('SELECT COUNT(*) FROM pdf_extractions') as cursor:
                    stats['total_processed'] = (await cursor.fetchone())[0]
                
                # Total amount processed
                async with db.execute('SELECT SUM(total_amount) FROM pdf_extractions WHERE total_amount IS NOT NULL') as cursor:
                    stats['total_amount'] = (await cursor.fetchone())[0] or 0
                
                # Pending count
                async with db.execute('SELECT COUNT(*) FROM pending_orders WHERE status = "pending"') as cursor:
                    stats['pending_count'] = (await cursor.fetchone())[0]
                
                return stats

# Add new API endpoints
@app.get("/api/invoices/date-range")
async def get_invoices_by_date_range(start_date: str, end_date: str):
    invoices = await db_manager.get_invoices_by_date_range(start_date, end_date)
    return {"invoices": invoices}

@app.get("/api/stats")
async def get_summary_stats():
    stats = await db_manager.get_summary_stats()
    return stats
```

### Database Migration

Handle database schema changes:

```python
class DatabaseMigration:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    async def migrate_to_v2(self):
        """Add new columns for version 2"""
        async with self.db_manager._lock:
            async with aiosqlite.connect(self.db_manager.db_path) as db:
                # Check current version
                try:
                    await db.execute('SELECT version FROM schema_version')
                    current_version = (await db.fetchone())[0]
                except:
                    current_version = 1
                    await db.execute('CREATE TABLE schema_version (version INTEGER)')
                    await db.execute('INSERT INTO schema_version (version) VALUES (1)')
                
                if current_version < 2:
                    # Add new columns
                    await db.execute('ALTER TABLE pdf_extractions ADD COLUMN purchase_order TEXT')
                    await db.execute('ALTER TABLE pdf_extractions ADD COLUMN department TEXT')
                    
                    # Update version
                    await db.execute('UPDATE schema_version SET version = 2')
                    await db.commit()
```

---

## Integration Customization

### Webhook Integration

Add webhook support for external integrations:

```python
import httpx

class WebhookService:
    def __init__(self, webhook_urls: list):
        self.webhook_urls = webhook_urls
    
    async def send_webhook(self, event: str, data: dict):
        async with httpx.AsyncClient() as client:
            for url in self.webhook_urls:
                try:
                    await client.post(url, json={
                        'event': event,
                        'timestamp': datetime.now().isoformat(),
                        'data': data
                    }, timeout=10.0)
                except Exception as e:
                    print(f"Webhook failed for {url}: {e}")

# Usage
webhook_service = WebhookService([
    "https://your-system.com/webhooks/pdf-processed",
    "https://accounting.company.com/api/invoice-received"
])

# Send webhook when PDF is processed
await webhook_service.send_webhook('pdf_processed', pdf_data.dict())
```

### External API Integration

Integrate with external services:

```python
class ExternalAPIIntegration:
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    async def validate_customer(self, customer_name: str) -> bool:
        """Validate customer against external CRM"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://crm-api.company.com/customers/search",
                params={'name': customer_name},
                headers={'Authorization': f'Bearer {self.api_key}'}
            )
            return response.status_code == 200 and len(response.json().get('results', [])) > 0
    
    async def get_tax_rate(self, zip_code: str) -> float:
        """Get tax rate from external tax service"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://tax-api.service.com/rates/{zip_code}",
                headers={'Authorization': f'Bearer {self.api_key}'}
            )
            if response.status_code == 200:
                return response.json().get('rate', 0.0)
            return 0.0

# Add validation to PDF processing
async def enhanced_pdf_processing(pdf_data: PDFExtractedData):
    api_integration = ExternalAPIIntegration(os.getenv('EXTERNAL_API_KEY'))
    
    # Validate customer
    if pdf_data.customer_name:
        is_valid_customer = await api_integration.validate_customer(pdf_data.customer_name)
        if not is_valid_customer:
            # Flag for manual review
            pdf_data.notes = f"{pdf_data.notes or ''}\nWarning: Customer not found in CRM".strip()
    
    return pdf_data
```

---

## Performance Customization

### Caching

Add caching for improved performance:

```python
import redis
import pickle

class CacheManager:
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_client = redis.from_url(redis_url)
    
    async def get_cached_extraction(self, file_hash: str) -> PDFExtractedData:
        cached = self.redis_client.get(f"pdf_extraction:{file_hash}")
        if cached:
            return pickle.loads(cached)
        return None
    
    async def cache_extraction(self, file_hash: str, pdf_data: PDFExtractedData, ttl: int = 3600):
        self.redis_client.setex(
            f"pdf_extraction:{file_hash}",
            ttl,
            pickle.dumps(pdf_data)
        )

# Use in PDF processing
import hashlib

def get_file_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()

cache_manager = CacheManager()

async def cached_extract_pdf_from_bytes(content: bytes, filename: str) -> PDFExtractedData:
    file_hash = get_file_hash(content)
    
    # Check cache first
    cached_result = await cache_manager.get_cached_extraction(file_hash)
    if cached_result:
        cached_result.filename = filename  # Update filename
        return cached_result
    
    # Extract and cache
    pdf_data = extract_pdf_from_bytes(content, filename)
    await cache_manager.cache_extraction(file_hash, pdf_data)
    
    return pdf_data
```

### Async Processing

Implement background task processing:

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

class BackgroundTaskManager:
    def __init__(self, max_workers: int = 4):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.tasks = {}
    
    def submit_task(self, task_id: str, func, *args, **kwargs):
        """Submit a background task"""
        future = self.executor.submit(func, *args, **kwargs)
        self.tasks[task_id] = future
        return task_id
    
    def get_task_status(self, task_id: str):
        """Get task status"""
        if task_id not in self.tasks:
            return {"status": "not_found"}
        
        future = self.tasks[task_id]
        if future.done():
            if future.exception():
                return {"status": "failed", "error": str(future.exception())}
            else:
                return {"status": "completed", "result": future.result()}
        else:
            return {"status": "processing"}

task_manager = BackgroundTaskManager()

@app.post("/api/batch-process")
async def batch_process_pdfs(files: List[UploadFile]):
    """Process multiple PDFs in background"""
    task_id = f"batch_{uuid.uuid4().hex[:8]}"
    
    def process_batch():
        results = []
        for file in files:
            try:
                content = file.file.read()
                pdf_data = extract_pdf_from_bytes(content, file.filename)
                results.append({"filename": file.filename, "status": "success", "data": pdf_data.dict()})
            except Exception as e:
                results.append({"filename": file.filename, "status": "error", "error": str(e)})
        return results
    
    task_manager.submit_task(task_id, process_batch)
    return {"task_id": task_id, "status": "started"}

@app.get("/api/batch-status/{task_id}")
async def get_batch_status(task_id: str):
    return task_manager.get_task_status(task_id)
```

This customization guide provides a comprehensive overview of how to extend and modify the PDF Processing System to meet your specific needs. The modular design makes it easy to add new features while maintaining the existing functionality.