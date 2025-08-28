# API Documentation

## Overview

The PDF Processing System provides a RESTful API built with FastAPI. All endpoints return JSON responses and support async operations.

## Base URL

```
http://localhost:8000
```

## Interactive API Documentation

FastAPI automatically generates interactive API documentation:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## Authentication

Currently, no authentication is required. For production use, consider implementing:

- API Key authentication
- JWT tokens
- OAuth2

## Core Endpoints

### Web Interface

#### GET `/`
Returns the main web interface.

**Response**: HTML page

---

### PDF Management

#### GET `/api/pdfs`
Get all processed PDFs.

**Response**:
```json
{
  "pdfs": [
    {
      "filename": "invoice_001.pdf",
      "invoice_number": "INV-2024-001",
      "customer_name": "John Doe",
      "customer_email": "john@example.com",
      "total_amount": 1500.00,
      "date_extracted": "2024-01-15T10:30:00",
      ...
    }
  ]
}
```

#### POST `/api/upload-pdf`
Upload a PDF file for immediate processing.

**Request**: Multipart form data with file

**Parameters**:
- `file`: PDF file (required)

**Response**:
```json
{
  "message": "PDF uploaded and processed successfully",
  "filename": "uploaded_file.pdf",
  "data": {
    "filename": "uploaded_file.pdf",
    "invoice_number": "INV-2024-002",
    ...
  }
}
```

**Error Responses**:
- `400`: Invalid file type
- `500`: Processing error

#### PUT `/api/pdfs/{filename}`
Update extracted data for a processed PDF.

**Parameters**:
- `filename`: PDF filename (path parameter)

**Request Body**:
```json
{
  "customer_name": "Updated Name",
  "total_amount": 2000.00,
  "notes": "Updated notes"
}
```

**Response**:
```json
{
  "message": "PDF data updated successfully",
  "data": {
    "filename": "invoice_001.pdf",
    "customer_name": "Updated Name",
    ...
  }
}
```

---

### Database Operations

#### POST `/api/commit/{filename}`
Commit processed PDF data to the database.

**Parameters**:
- `filename`: PDF filename (path parameter)

**Response**:
```json
{
  "message": "Data committed to database successfully"
}
```

**Error Response**:
```json
{
  "error": "PDF not found"
}
```

#### GET `/api/database`
Get all records from the database.

**Response**:
```json
{
  "records": [
    {
      "id": 1,
      "filename": "invoice_001.pdf",
      "invoice_number": "INV-2024-001",
      "customer_name": "John Doe",
      "created_at": "2024-01-15T10:30:00",
      ...
    }
  ]
}
```

---

### Pending Orders

#### POST `/api/pending/{filename}`
Send a processed PDF to pending orders for review.

**Parameters**:
- `filename`: PDF filename (path parameter)

**Response**:
```json
{
  "message": "Order sent to pending successfully"
}
```

#### GET `/api/pending`
Get all pending orders.

**Response**:
```json
{
  "orders": [
    {
      "id": 1,
      "filename": "invoice_001.pdf",
      "pdf_data": "{...json serialized data...}",
      "status": "pending",
      "created_at": "2024-01-15T10:30:00",
      "updated_at": "2024-01-15T10:30:00"
    }
  ]
}
```

#### GET `/api/pending/count`
Get count of pending orders.

**Response**:
```json
{
  "count": 5
}
```

#### PUT `/api/pending/{order_id}`
Update a pending order.

**Parameters**:
- `order_id`: Pending order ID (path parameter)

**Request Body**:
```json
{
  "customer_name": "Updated Name",
  "total_amount": 1800.00,
  "invoice_number": "INV-2024-001-UPDATED"
}
```

**Response**:
```json
{
  "message": "Pending order updated successfully"
}
```

---

### Schema Information

#### GET `/api/model-schema`
Get the Pydantic model schema for dynamic form generation.

**Response**:
```json
{
  "fields": {
    "invoice_number": {
      "type": "string",
      "description": "Invoice or order number",
      "required": false
    },
    "total_amount": {
      "type": "number",
      "description": "Total amount",
      "required": false
    },
    ...
  }
}
```

---

## Data Models

### PDFExtractedData

The main data model for extracted PDF information:

```json
{
  "filename": "string",
  "invoice_number": "string (optional)",
  "customer_name": "string (optional)",
  "customer_email": "string (optional)",
  "order_date": "string (optional)",
  "due_date": "string (optional)",
  "total_amount": "number (optional)",
  "tax_amount": "number (optional)",
  "currency": "string (default: USD)",
  "items_description": "string (optional)",
  "quantity": "integer (optional)",
  "unit_price": "number (optional)",
  "billing_address": "string (optional)",
  "shipping_address": "string (optional)",
  "vendor_name": "string (optional)",
  "payment_terms": "string (optional)",
  "notes": "string (optional)",
  "content_preview": "string",
  "full_text": "string",
  "date_extracted": "datetime"
}
```

### Error Responses

Standard error response format:

```json
{
  "error": "Error description",
  "detail": "Additional error details"
}
```

Common HTTP status codes:
- `200`: Success
- `400`: Bad Request
- `404`: Not Found
- `422`: Validation Error
- `500`: Internal Server Error

---

## Usage Examples

### Python with requests

```python
import requests

# Upload PDF
with open('invoice.pdf', 'rb') as f:
    files = {'file': f}
    response = requests.post('http://localhost:8000/api/upload-pdf', files=files)
    print(response.json())

# Get processed PDFs
response = requests.get('http://localhost:8000/api/pdfs')
pdfs = response.json()['pdfs']

# Update PDF data
update_data = {'customer_name': 'New Name', 'total_amount': 2000.00}
response = requests.put(f'http://localhost:8000/api/pdfs/{filename}', json=update_data)

# Commit to database
response = requests.post(f'http://localhost:8000/api/commit/{filename}')
```

### JavaScript/Fetch

```javascript
// Upload PDF
const formData = new FormData();
formData.append('file', pdfFile);

fetch('/api/upload-pdf', {
    method: 'POST',
    body: formData
})
.then(response => response.json())
.then(data => console.log(data));

// Get processed PDFs
fetch('/api/pdfs')
.then(response => response.json())
.then(data => console.log(data.pdfs));

// Update PDF data
fetch(`/api/pdfs/${filename}`, {
    method: 'PUT',
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        customer_name: 'Updated Name',
        total_amount: 2000.00
    })
})
.then(response => response.json())
.then(data => console.log(data));
```

### curl

```bash
# Upload PDF
curl -X POST "http://localhost:8000/api/upload-pdf" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@invoice.pdf"

# Get processed PDFs
curl -X GET "http://localhost:8000/api/pdfs"

# Update PDF data
curl -X PUT "http://localhost:8000/api/pdfs/invoice.pdf" \
  -H "Content-Type: application/json" \
  -d '{"customer_name": "Updated Name", "total_amount": 2000.00}'

# Commit to database
curl -X POST "http://localhost:8000/api/commit/invoice.pdf"
```

---

## Rate Limiting

Currently, no rate limiting is implemented. For production use, consider:

- Request rate limiting per IP
- File size limits for uploads
- Concurrent request limits

## Error Handling

The API uses standard HTTP status codes and returns detailed error messages in JSON format. Always check the response status code and handle errors appropriately in your client applications.

## WebSocket Support

Currently not implemented, but could be added for real-time updates of processing status and pending order changes.