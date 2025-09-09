"""
Configurable PDF Processing Module

This module provides a single, replaceable function for PDF processing.
Replace the `process_pdf_content` function with your own logic.
"""
import re
from datetime import datetime
from typing import Any, Dict, Type
from pydantic import BaseModel
import PyPDF2
from io import BytesIO


def process_pdf_content(
    text: str, 
    filename: str, 
    model_class: Type[BaseModel]
) -> BaseModel:
    """
    REPLACE THIS FUNCTION WITH YOUR OWN PDF PROCESSING LOGIC
    
    This is the single point where PDF text is converted to structured data.
    
    Args:
        text: Extracted PDF text content
        filename: Name of the PDF file
        model_class: Pydantic model class to instantiate
        
    Returns:
        Instance of model_class with extracted data
        
    Example:
        To replace with your logic, modify this function:
        
        def process_pdf_content(text, filename, model_class):
            # Your custom processing logic here
            data = your_parsing_logic(text)
            return model_class(**data)
    """
    
    # Default implementation - replace this entire function
    content_preview = text[:200] if text else "No content extracted"
    
    # Mock field extraction (replace with your logic)
    invoice_match = re.search(r'invoice[#\s]+([A-Z0-9-]+)', text, re.IGNORECASE)
    total_match = re.search(r'total[:\s]*\$?([0-9,]+\.?[0-9]*)', text, re.IGNORECASE)
    email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', text)
    date_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', text)
    
    # Build data dictionary based on model fields
    data = {
        'filename': filename,
        'content_preview': content_preview,
        'full_text': text,
        'date_extracted': datetime.now()
    }
    
    # Add extracted fields if they exist in the model
    model_fields = model_class.model_fields.keys()
    
    if 'invoice_number' in model_fields and invoice_match:
        data['invoice_number'] = invoice_match.group(1)
    if 'total_amount' in model_fields and total_match:
        try:
            data['total_amount'] = float(total_match.group(1).replace(',', ''))
        except:
            pass
    if 'customer_email' in model_fields and email_match:
        data['customer_email'] = email_match.group(1)
    if 'order_date' in model_fields and date_match:
        data['order_date'] = date_match.group(1)
    if 'currency' in model_fields:
        data['currency'] = 'USD'
    
    # Filter data to only include fields that exist in the model
    filtered_data = {k: v for k, v in data.items() if k in model_fields}
    
    return model_class(**filtered_data)


def extract_pdf_from_file(file_path: str, model_class: Type[BaseModel]) -> BaseModel:
    """
    Extract PDF data from file path using the configurable processor
    
    Args:
        file_path: Path to PDF file
        model_class: Pydantic model class to instantiate
        
    Returns:
        Instance of model_class with extracted data
    """
    try:
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
        
        import os
        filename = os.path.basename(file_path)
        return process_pdf_content(text, filename, model_class)
        
    except Exception as e:
        # Return error instance
        data = {
            'filename': os.path.basename(file_path) if 'file_path' in locals() else 'unknown',
            'date_extracted': datetime.now()
        }
        
        model_fields = model_class.model_fields.keys()
        if 'content_preview' in model_fields:
            data['content_preview'] = f'Error processing PDF: {str(e)}'
        if 'full_text' in model_fields:
            data['full_text'] = ''
            
        # Filter data to model fields
        filtered_data = {k: v for k, v in data.items() if k in model_fields}
        return model_class(**filtered_data)


def extract_pdf_from_bytes(content: bytes, filename: str, model_class: Type[BaseModel]) -> BaseModel:
    """
    Extract PDF data from bytes content using the configurable processor
    
    Args:
        content: PDF file content as bytes
        filename: Name of the PDF file
        model_class: Pydantic model class to instantiate
        
    Returns:
        Instance of model_class with extracted data
    """
    try:
        reader = PyPDF2.PdfReader(BytesIO(content))
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        
        return process_pdf_content(text, filename, model_class)
        
    except Exception as e:
        # Return error instance
        data = {
            'filename': filename,
            'date_extracted': datetime.now()
        }
        
        model_fields = model_class.model_fields.keys()
        if 'content_preview' in model_fields:
            data['content_preview'] = f'Error processing uploaded PDF: {str(e)}'
        if 'full_text' in model_fields:
            data['full_text'] = ''
            
        # Filter data to model fields
        filtered_data = {k: v for k, v in data.items() if k in model_fields}
        return model_class(**filtered_data)


def get_model_schema_for_template(model_class: Type[BaseModel]) -> Dict[str, Any]:
    """
    Extract Pydantic model schema information for template rendering
    
    Args:
        model_class: Pydantic model class
        
    Returns:
        Dictionary with field information suitable for Jinja templates
    """
    schema = model_class.model_json_schema()
    
    fields = {}
    properties = schema.get('properties', {})
    required_fields = set(schema.get('required', []))
    
    for field_name, field_info in properties.items():
        # Skip system/internal fields
        if field_name in ['date_extracted']:
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
            'required': field_name in required_fields,
            'display_name': field_name.replace('_', ' ').title()
        }
    
    return {
        'model_name': model_class.__name__,
        'fields': fields
    }