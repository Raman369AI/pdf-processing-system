# PDF Processing System

A FastAPI-based PDF processing system with dynamic field extraction, queue management, and web interface. Built for commercial use with minimal dependencies and robust architecture.

## 🚀 Features

### Core Functionality
- **Automatic PDF Monitoring**: Watches local folder for new PDFs using Watchdog
- **Direct PDF Upload**: Drag & drop or click to upload PDFs directly through web interface
- **Dynamic Field Extraction**: Pydantic model-driven form generation that adapts automatically
- **Queue Management**: Background processing queue separate from web interface
- **Pending Orders System**: Review and modify extracted data before database commit
- **Real-time Updates**: Live refresh of processed PDFs and pending counts

### Technical Highlights
- **FastAPI Backend**: Async Python web framework with automatic API documentation
- **Pydantic Models**: Type-safe data validation and dynamic form generation
- **aiosqlite Database**: Async SQLite operations with lock prevention
- **Responsive Frontend**: Clean HTML/CSS/JavaScript interface with modal dialogs
- **Commercial Ready**: Minimal dependencies, optimized for local deployment

### Data Extraction Fields
- **Invoice Information**: Invoice number, dates, customer details
- **Financial Data**: Total amount, tax amount, currency, payment terms
- **Customer Information**: Name, email, billing/shipping addresses
- **Product Details**: Items description, quantity, unit price
- **Vendor Information**: Vendor name, payment terms, notes

## 📋 Prerequisites

- Python 3.8+
- Git (for repository management)
- Modern web browser

## 🛠️ Installation

### 1. Clone the Repository
```bash
git clone https://github.com/Raman369AI/pdf-processing-system.git
cd pdf-processing-system
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Application
```bash
python main.py
```

### 4. Access the Web Interface
Open your browser and navigate to: `http://localhost:8000`

## 📁 Project Structure

```
pdf-processing-system/
│
├── main.py                 # FastAPI application and core logic
├── models.py               # Pydantic data models
├── requirements.txt        # Python dependencies
├── README.md              # This documentation
├── LICENSE                # MIT License
│
├── templates/
│   └── index.html         # Web interface template
│
├── static/                # Static files (CSS, JS) - auto-created
├── pdfs/                  # PDF monitoring folder - auto-created
│
├── docs/                  # Additional documentation
│   ├── API.md            # API documentation
│   ├── DEPLOYMENT.md     # Deployment guide
│   └── CUSTOMIZATION.md  # Customization guide
│
└── pdf_data.db           # SQLite database - auto-created
```

## 🔄 Usage

### Automatic PDF Processing
1. **Add PDFs to Folder**: Drop PDF files into the `pdfs/` folder
2. **Automatic Detection**: System monitors and processes files automatically
3. **View Results**: Check the web interface for extracted data
4. **Edit Fields**: Modify any extracted fields through dynamic forms
5. **Commit or Send to Pending**: Choose to save to database or review later

### Direct PDF Upload
1. **Access Upload Area**: Use the upload section on the main page
2. **Drag & Drop**: Drop PDF files directly onto the upload zone
3. **Click to Upload**: Alternative click-to-select file option
4. **Instant Processing**: Files processed immediately without queue
5. **Same Workflow**: Use same edit/commit workflow as monitored files

### Pending Orders Management
1. **Send to Pending**: Use "Send to Pending" button for any processed PDF
2. **View Pending**: Click the pending badge in the header
3. **Edit Orders**: Modify key fields in the popup modal
4. **Update Orders**: Save changes to pending orders
5. **Track Count**: Real-time pending count display

## 🛠️ API Endpoints

### Core Endpoints
- `GET /` - Web interface
- `GET /api/pdfs` - List all processed PDFs
- `POST /api/upload-pdf` - Upload PDF directly
- `PUT /api/pdfs/{filename}` - Update PDF data

### Database Operations
- `POST /api/commit/{filename}` - Commit PDF to database
- `GET /api/database` - Get all database records

### Pending Orders
- `POST /api/pending/{filename}` - Send PDF to pending
- `GET /api/pending` - Get pending orders
- `GET /api/pending/count` - Get pending count
- `PUT /api/pending/{order_id}` - Update pending order

### Schema
- `GET /api/model-schema` - Get Pydantic model schema for dynamic forms

## ⚙️ Configuration

### Environment Variables
The system uses sensible defaults but can be configured via environment variables:

```bash
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

## 🚀 Deployment

### Local Development
```bash
python main.py
```

### Production Deployment
```bash
# Using Uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8000

# Using Gunicorn
gunicorn main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Docker Deployment
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 🧪 Testing

### Manual Testing
1. **Start Application**: `python main.py`
2. **Add Test PDF**: Drop a PDF into `pdfs/` folder
3. **Check Processing**: Verify extraction in web interface
4. **Test Upload**: Upload PDF through web interface
5. **Test Pending**: Send order to pending and modify
6. **Test Database**: Commit data and check database records

### Automated Testing
```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests (when test files are added)
pytest tests/
```

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