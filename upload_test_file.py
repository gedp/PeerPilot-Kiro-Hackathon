#!/usr/bin/env python3
"""
Upload PDF file to trigger Lambda function properly
"""

from src.s3_client import S3Client
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Upload a PDF file to trigger the Lambda function"""
    
    # Initialize S3 client
    s3_client = S3Client()
    
    # List existing PDFs in the input-articles folder
    print("Checking existing PDF files in input-articles/...")
    files = s3_client.list_files("input-articles/")
    pdf_files = [f for f in files if f.endswith('.pdf')]
    
    print(f"Found {len(pdf_files)} PDF files:")
    for pdf in pdf_files:
        print(f"  - {pdf}")
    
    if pdf_files:
        # Download and re-upload the first PDF to trigger the function
        source_pdf = pdf_files[0]
        print(f"\nDownloading {source_pdf} to re-upload...")
        
        # Download the PDF
        local_filename = "temp_test.pdf"
        s3_client.download_file(source_pdf, local_filename)
        
        # Create a new filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_pdf_name = f"test_trigger_{timestamp}.pdf"
        
        print(f"Re-uploading as {new_pdf_name} to trigger Lambda...")
        
        # Upload with new name to trigger the function
        s3_client.upload_file(local_filename, f"input-articles/{new_pdf_name}")
        
        print(f"✅ PDF uploaded successfully to input-articles/{new_pdf_name}")
        print("This should trigger the Lambda function with a proper PDF!")
        
        # Clean up local file
        import os
        os.remove(local_filename)
        print("Local temp file cleaned up.")
        
    else:
        print("❌ No PDF files found in input-articles/ folder!")
        print("Please upload a PDF file manually to test the function.")

if __name__ == "__main__":
    main()