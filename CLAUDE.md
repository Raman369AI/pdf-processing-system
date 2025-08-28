# DEVELOPMENT.md

This file provides development guidance when working with code in this repository.

## Repository Overview

A FastAPI-based PDF processing system that monitors a local folder for PDFs, processes them with field extraction, and provides a web interface for managing results. Commercial-ready with minimal dependencies.

## Development Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py

# Access web interface
http://localhost:8000
```

## Architecture

- **main.py**: FastAPI application with async SQLite operations using aiosqlite
- **DatabaseManager**: Async database operations with locking to prevent database locks
- **PDFHandler**: Watchdog-based file system monitoring for the `pdfs/` folder
- **Background Processing**: Separate thread processes PDF queue using PyPDF2
- **In-memory Storage**: Simple queue and dictionary for PDF processing state
- **Web Interface**: Single-page HTML frontend with JavaScript for real-time updates

## Key Components

- PDF folder monitoring with automatic processing
- Async SQLite database operations to prevent locks
- Background thread separation for PDF processing
- Simple web interface for viewing and committing results
- INSERT OR REPLACE pattern for database uniqueness