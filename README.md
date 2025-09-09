# PDF Processing System

A fault-tolerant, scalable PDF processing system built with FastAPI, Celery, and Redis. Features automatic PDF monitoring, configurable field extraction, and a dynamic web interface that adapts to your Pydantic models.

## 🚀 Features

### Core Functionality
- **Fault-Tolerant Processing**: Celery with Redis provides persistent queues and automatic retries
- **Automatic PDF Monitoring**: Standalone service watches folder for new PDFs
- **Direct PDF Upload**: Drag & drop interface for immediate processing
- **Configurable Processing**: Single function to replace with your custom logic
- **Dynamic Web Interface**: Auto-adapts to your Pydantic model changes
- **Scalable Architecture**: Independent services can be scaled separately

### Technical Highlights
- **Separated Services**: File monitor, workers, and web app run independently
- **Celery Task Queue**: Persistent, fault-tolerant background processing
- **Redis Backend**: Message broker with persistence across restarts
- **Dynamic Templates**: Jinja templates adapt to any Pydantic model
- **Database-Centric**: All data persisted, no in-memory state
- **Multi-Worker Safe**: Scale FastAPI and Celery workers without conflicts

### Data Extraction Fields
- **Invoice Information**: Invoice number, dates, customer details
- **Financial Data**: Total amount, tax amount, currency, payment terms
- **Customer Information**: Name, email, billing/shipping addresses
- **Product Details**: Items description, quantity, unit price
- **Vendor Information**: Vendor name, payment terms, notes

## 📋 Prerequisites

- Python 3.8+
- Redis server
- Modern web browser

## 🛠️ Installation

### 1. Clone and Install Dependencies
```bash
git clone <repository>
cd utilities
pip install -r requirements.txt
```

### 2. Start Services (in separate terminals)

```bash
# Terminal 1: Start Redis
redis-server

# Terminal 2: Start Celery worker
celery -A worker worker --loglevel=info

# Terminal 3: Start PDF monitor
python pdf_monitor.py

# Terminal 4: Start web application
python main.py
```

### 3. Access the Web Interface
Open your browser and navigate to: `http://localhost:8000`

## 📁 Project Structure

```
utilities/
│
├── main.py              # FastAPI web application
├── worker.py            # Celery worker for PDF processing
├── pdf_monitor.py       # File system monitoring service
├── pdf_processor.py     # Configurable PDF processing logic
├── models.py            # Pydantic data models
├── process_existing.py  # Utility for processing existing PDFs
├── requirements.txt     # Python dependencies
├── README.md           # This documentation
├── CLAUDE.md           # Development guidance
│
├── templates/
│   └── dynamic_form.html # Auto-adapting web interface
│
├── pdfs/               # PDF input folder (auto-created)
└── pdf_data.db         # SQLite database (auto-created)
```

## 🔧 Customizing PDF Processing

The system is designed for easy customization. Replace the processing logic in one place:

### Edit `pdf_processor.py`

```python
def process_pdf_content(text: str, filename: str, model_class: Type[BaseModel]) -> BaseModel:
    """
    REPLACE THIS FUNCTION WITH YOUR OWN PDF PROCESSING LOGIC
    
    Args:
        text: Extracted PDF text content
        filename: Name of the PDF file  
        model_class: Pydantic model class to instantiate
        
    Returns:
        Instance of model_class with extracted data
    """
    
    # Your custom processing logic here
    data = {
        'filename': filename,
        'your_field': extract_your_data(text),
        'another_field': parse_something_else(text),
        # ... extract whatever fields your model needs
    }
    
    return model_class(**data)
```

### Update Your Data Model

Modify `models.py` to define your fields:

```python
from pydantic import BaseModel
from datetime import datetime

class YourDataModel(BaseModel):
    filename: str
    your_field: str | None = None
    another_field: float | None = None
    date_extracted: datetime
    # Add any fields you need
```

The web interface **automatically adapts** to your model changes!

## 🔄 Usage & Workflow Options

### **Option 1: Automatic Folder Monitoring (No Manual Triggers)**
1. **Add PDFs to Folder**: Drop PDF files into the `pdfs/` folder
2. **Auto-Detection**: `pdf_monitor.py` automatically detects new files
3. **Auto-Processing**: Celery worker processes PDF using your custom logic
4. **Auto-Storage**: Results automatically saved to database
5. **Zero Intervention**: Completely hands-off processing

### **Option 2: API Upload to Monitored Folder**
1. **API Upload**: `POST /api/upload-pdf-to-folder` with PDF file
2. **File Saved**: PDF saved to monitored folder with unique name
3. **Auto-Processing**: Monitor detects → Celery processes → Database storage
4. **Status Tracking**: Use `GET /api/processing-status/{filename}` to track

### **Option 3: Direct Processing Upload**
1. **Web Upload**: Drag & drop PDFs on web interface
2. **Direct Processing**: Files bypass folder, go straight to Celery
3. **Task Tracking**: Use `GET /api/task-status/{task_id}` to monitor
4. **Database Storage**: Results saved when processing completes

### Pending Orders Management
1. **Send to Pending**: Use "Send to Pending" button for any processed PDF
2. **View Pending**: Click the pending badge in the header
3. **Edit Orders**: Modify key fields in the popup modal
4. **Update Orders**: Save changes to pending orders
5. **Track Count**: Real-time pending count display

## 🛠️ API Endpoints

### **File Upload & Processing**
- `POST /api/upload-pdf` - Upload PDF for direct Celery processing
- `POST /api/upload-pdf-to-folder` - Upload PDF to monitored folder  
- `GET /api/task-status/{task_id}` - Get Celery task status and results
- `GET /api/processing-status/{filename}` - Check PDF processing status by filename

### **Data Management**
- `GET /` - Dynamic web interface (auto-adapts to your model)
- `GET /api/pdfs` - List all processed PDFs from database
- `PUT /api/pdfs/{filename}` - Update PDF extracted data
- `GET /api/database` - Get all database records

### **Pending Orders**
- `POST /api/commit/{filename}` - Commit PDF data to database
- `POST /api/pending/{filename}` - Send PDF to pending orders
- `GET /api/pending` - List all pending orders
- `GET /api/pending/count` - Get pending orders count
- `PUT /api/pending/{order_id}` - Update pending order data

### **Schema & Configuration**
- `GET /api/model-schema` - Get Pydantic model schema for dynamic forms

## 📖 API Usage Examples

### **Upload PDF to Monitored Folder**
```bash
curl -X POST -F "file=@document.pdf" \
  http://localhost:8000/api/upload-pdf-to-folder
```

**Response:**
```json
{
  "message": "PDF uploaded to monitored folder for automatic processing",
  "filename": "document.pdf",
  "unique_filename": "abc123_document.pdf", 
  "file_path": "pdfs/abc123_document.pdf",
  "monitoring_info": "File will be automatically detected and processed"
}
```

### **Check Processing Status**
```bash
curl http://localhost:8000/api/processing-status/document.pdf
```

**Response:**
```json
{
  "status": "completed",
  "filename": "document.pdf",
  "processed": true,
  "data": { /* extracted PDF data */ },
  "message": "PDF has been processed and stored in database"
}
```

**Status Types:**
- `"completed"` - Processed and stored in database
- `"pending"` - Processed but in pending orders  
- `"processing"` - Currently being processed
- `"not_found"` - PDF not found in system

### **Check Task Status (for direct uploads)**
```bash
curl http://localhost:8000/api/task-status/abc-123-task-id
```

**Response:**
```json
{
  "state": "SUCCESS",
  "status": "Task completed successfully",
  "result": {
    "status": "success", 
    "filename": "document.pdf",
    "message": "Successfully processed document.pdf"
  }
}
```

## ⚙️ Configuration

### Environment Variables
The system uses sensible defaults but can be configured via environment variables:

```bash
# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Database
DATABASE_URL=sqlite:///./pdf_data.db

# PDF Processing  
PDF_FOLDER_PATH=./pdfs

# Server
HOST=0.0.0.0
PORT=8000
```

### Customizing Data Models
Edit `models.py` to add/remove/modify extracted fields:

```python
class PDFExtractedData(BaseModel):
    # Add new fields here
    new_field: Optional[str] = Field(None, description="New field description")
```

The frontend will automatically adapt to model changes.

## 📊 Database Schema

### PDF Extractions Table
```sql
CREATE TABLE pdf_extractions (
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
);
```

### Pending Orders Table
```sql
CREATE TABLE pending_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    pdf_data TEXT NOT NULL,  -- JSON serialized PDFExtractedData
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 🔧 Customization

### Adding New Fields
1. **Update Model**: Add fields to `PDFExtractedData` in `models.py`
2. **Update Database**: The system will auto-create new columns
3. **Update Extraction**: Modify `extract_pdf_fields()` function for new parsing logic
4. **Frontend Adapts**: Forms automatically include new fields

### Custom PDF Processing
Modify the `extract_pdf_fields()` function in `main.py`:

```python
def extract_pdf_fields(text: str, filename: str) -> PDFExtractedData:
    # Add your custom extraction logic here
    custom_field_match = re.search(r'your_pattern', text, re.IGNORECASE)
    
    return PDFExtractedData(
        # ... existing fields
        custom_field=custom_field_match.group(1) if custom_field_match else None
    )
```

### UI Customization
- **Styling**: Modify CSS in `templates/index.html`
- **Layout**: Adjust HTML structure in template
- **Behavior**: Update JavaScript functions for custom interactions

## 🎨 Dynamic Web Interface

The Jinja template system automatically adapts to your Pydantic model:

- **Dynamic fields** - Form fields generated from model schema
- **Smart input types** - Number inputs for numeric fields, text for strings  
- **Auto-labels** - Readable field names from model definitions
- **Responsive design** - Beautiful UI that works on any device

## 🔍 How It Works

### **Automatic Processing Flow**
1. **File Detection** - `pdf_monitor.py` watches the `pdfs/` folder independently  
2. **Task Queue** - New PDFs automatically trigger Celery tasks in Redis
3. **Background Processing** - Worker processes PDF using your custom logic
4. **Auto-Storage** - Results automatically saved to SQLite database
5. **Status Tracking** - Check processing status via API endpoints

### **Manual Upload Options**
- **To Folder**: Upload via API → Saved to folder → Auto-detected → Processed
- **Direct Processing**: Upload via API → Straight to Celery → Processed
- **Web Interface**: Drag & drop → Direct processing → Real-time updates

## 🐳 Docker Deployment

Create `docker-compose.yml`:

```yaml
version: '3.8'
services:
  redis:
    image: redis:alpine
    
  worker:
    build: .
    command: celery -A worker worker --loglevel=info
    depends_on: [redis]
    volumes:
      - ./pdfs:/app/pdfs
      
  monitor:
    build: .
    command: python pdf_monitor.py
    depends_on: [redis, worker]
    volumes:
      - ./pdfs:/app/pdfs
      
  web:
    build: .
    command: python main.py
    ports: ["8000:8000"]
    depends_on: [redis]
```

## 🔍 Monitoring

### Check Service Status

```bash
# Check Celery workers
celery -A worker inspect active

# Check Redis connection
redis-cli ping

# Monitor logs
tail -f /var/log/pdf-processing/*.log
```

### Processing Existing PDFs

```bash
# Process all PDFs in the folder
python process_existing.py
```

## 🚨 Troubleshooting

### Common Issues

1. **Redis connection failed**
   ```bash
   # Start Redis server
   redis-server
   ```

2. **No Celery workers**
   ```bash
   # Start worker with verbose logging
   celery -A worker worker --loglevel=debug
   ```

3. **PDF not processing**
   - Check `pdfs/` folder exists and has read permissions
   - Verify `pdf_monitor.py` is running
   - Check worker logs for errors

4. **Database locked**
   - SQLite uses file locking - ensure only one process writes
   - Check file permissions on `pdf_data.db`

### Logs

- **Worker logs**: Celery worker output shows processing status
- **Monitor logs**: File system events and task submission
- **Web logs**: HTTP requests and API responses

## 🔒 Security Considerations

### File Upload Security
- **File Type Validation**: Only PDF files accepted
- **File Size Limits**: Implement limits for production use
- **Virus Scanning**: Consider adding virus scanning for uploads

### Database Security
- **Async Locks**: Prevents SQLite locking issues
- **Input Validation**: Pydantic models validate all data
- **SQL Injection**: Uses parameterized queries

### Access Control
- **Local Network**: Designed for local/trusted network use
- **Authentication**: Add authentication for production deployment
- **HTTPS**: Use reverse proxy with SSL for production

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make changes and test thoroughly
4. Commit changes: `git commit -m 'Add amazing feature'`
5. Push to branch: `git push origin feature/amazing-feature`
6. Create a Pull Request

### Code Style
- Follow PEP 8 for Python code
- Use type hints where possible
- Add docstrings for functions
- Keep functions focused and small

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

### Issues
- **Bug Reports**: Use GitHub Issues for bug reports
- **Feature Requests**: Use GitHub Issues with "enhancement" label
- **Questions**: Use GitHub Discussions for general questions

### Documentation
- **API Documentation**: Available at `http://localhost:8000/docs` when running
- **Additional Docs**: Check the `docs/` folder for detailed guides

## 🎯 Roadmap

### Upcoming Features
- [ ] Advanced PDF parsing with AI/ML
- [ ] Multi-language support
- [ ] Batch processing capabilities
- [ ] API key authentication
- [ ] Export to multiple formats (CSV, Excel, JSON)
- [ ] Advanced search and filtering
- [ ] Email notifications
- [ ] Webhook integrations

### Version History
- **v1.0.0**: Initial release with core functionality
- **v1.1.0**: Added direct PDF upload feature
- **v1.2.0**: Enhanced pending orders system
- **v1.3.0**: Dynamic form generation from Pydantic models

## 🙏 Acknowledgments

- FastAPI for the excellent async web framework
- Pydantic for data validation and settings management
- SQLite for reliable local database storage
- PyPDF2 for PDF text extraction
- Watchdog for file system monitoring

---

**Built with ❤️ for efficient PDF processing and data extraction**