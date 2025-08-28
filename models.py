from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum

class OrderStatus(str, Enum):
    PROCESSED = "processed"
    PENDING = "pending"
    COMPLETED = "completed"

class PDFExtractedData(BaseModel):
    """Pydantic model for structured PDF data extraction"""
    filename: str = Field(..., description="PDF filename")
    
    # Invoice/Order fields
    invoice_number: Optional[str] = Field(None, description="Invoice or order number")
    customer_name: Optional[str] = Field(None, description="Customer name")
    customer_email: Optional[str] = Field(None, description="Customer email")
    order_date: Optional[str] = Field(None, description="Order date")
    due_date: Optional[str] = Field(None, description="Due date")
    
    # Financial fields
    total_amount: Optional[float] = Field(None, description="Total amount")
    tax_amount: Optional[float] = Field(None, description="Tax amount")
    currency: Optional[str] = Field("USD", description="Currency code")
    
    # Product/Service fields
    items_description: Optional[str] = Field(None, description="Items or services description")
    quantity: Optional[int] = Field(None, description="Quantity of items")
    unit_price: Optional[float] = Field(None, description="Unit price")
    
    # Address fields
    billing_address: Optional[str] = Field(None, description="Billing address")
    shipping_address: Optional[str] = Field(None, description="Shipping address")
    
    # Additional metadata
    vendor_name: Optional[str] = Field(None, description="Vendor or supplier name")
    payment_terms: Optional[str] = Field(None, description="Payment terms")
    notes: Optional[str] = Field(None, description="Additional notes")
    
    # System fields
    content_preview: str = Field(..., description="Content preview")
    full_text: str = Field("", description="Full extracted text")
    date_extracted: datetime = Field(default_factory=datetime.now, description="Extraction timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class PendingOrder(BaseModel):
    """Pydantic model for pending orders"""
    id: Optional[int] = None
    pdf_data: PDFExtractedData
    status: OrderStatus = OrderStatus.PENDING
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class PDFDataUpdate(BaseModel):
    """Model for updating PDF data fields"""
    invoice_number: Optional[str] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    order_date: Optional[str] = None
    due_date: Optional[str] = None
    total_amount: Optional[float] = None
    tax_amount: Optional[float] = None
    currency: Optional[str] = None
    items_description: Optional[str] = None
    quantity: Optional[int] = None
    unit_price: Optional[float] = None
    billing_address: Optional[str] = None
    shipping_address: Optional[str] = None
    vendor_name: Optional[str] = None
    payment_terms: Optional[str] = None
    notes: Optional[str] = None