#!/usr/bin/env python3
"""
Test script for document processing functionality
"""

import os
import tempfile
from src.document_processor import DocumentProcessor
from src.s3_client import S3Client

def create_sample_pdf():
    """Create a simple PDF for testing (using reportlab if available)"""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            c = canvas.Canvas(temp_file.name, pagesize=letter)
            c.drawString(100, 750, "PeerPilot Test Document")
            c.drawString(100, 700, "This is a sample academic article for testing.")
            c.drawString(100, 650, "Abstract: This paper demonstrates the automated")
            c.drawString(100, 600, "processing capabilities of PeerPilot AI agent.")
            c.drawString(100, 550, "Keywords: AI, automation, peer review")
            c.save()
            return temp_file.name
    except ImportError:
        print("⚠️  reportlab not installed. Please upload a real PDF for testing.")
        return None

def test_document_processing():
    """Test the complete document processing pipeline"""
    print("🚀 Testing Document Processing Pipeline...")
    
    try:
        # Initialize components
        s3_client = S3Client()
        processor = DocumentProcessor()
        
        print("✅ Components initialized successfully")
        
        # Ensure bucket exists
        if not s3_client.create_bucket_if_not_exists():
            print("❌ Failed to create/verify bucket")
            return False
        
        # Create or use sample PDF
        sample_pdf = create_sample_pdf()
        if not sample_pdf:
            print("📄 Please place a PDF file in the current directory named 'test_article.pdf'")
            if os.path.exists('test_article.pdf'):
                sample_pdf = 'test_article.pdf'
            else:
                print("❌ No test PDF available")
                return False
        
        # Upload PDF to articulos-entrada folder
        pdf_key = "articulos-entrada/test_article.pdf"
        print(f"\n📤 Uploading test PDF to {pdf_key}...")
        
        if not s3_client.upload_file(sample_pdf, pdf_key):
            print("❌ Failed to upload test PDF")
            return False
        
        print("✅ PDF uploaded successfully")
        
        # Process the document
        print("\n🔄 Processing document with Textract...")
        result = processor.process_uploaded_pdf(pdf_key)
        
        if result['status'] == 'success':
            print("✅ Document processed successfully!")
            print(f"   Original file: {result['original_file']}")
            print(f"   Text file: {result['text_file']}")
            print(f"   Text length: {result['text_length']} characters")
            
            # Verify processed files exist
            print("\n📋 Verifying processed files...")
            processed_files = processor.list_processed_articles()
            
            expected_files = [
                result['text_file'].replace('processed-articles/', ''),
                result['metadata_file'].replace('processed-articles/', '')
            ]
            
            for expected_file in expected_files:
                if any(expected_file in f for f in processed_files):
                    print(f"✅ Found: {expected_file}")
                else:
                    print(f"❌ Missing: {expected_file}")
            
            # Test retrieving processed text
            print("\n📖 Testing text retrieval...")
            article_name = os.path.splitext(os.path.basename(pdf_key))[0]
            extracted_text = processor.get_processed_text(article_name)
            
            if extracted_text:
                print(f"✅ Retrieved text ({len(extracted_text)} characters)")
                print(f"   Preview: {extracted_text[:100]}...")
            else:
                print("❌ Failed to retrieve processed text")
            
        else:
            print(f"❌ Document processing failed: {result.get('error', 'Unknown error')}")
            return False
        
        # Cleanup
        print("\n🧹 Cleaning up test files...")
        s3_client.delete_file(pdf_key)
        if result['status'] == 'success':
            s3_client.delete_file(result['text_file'])
            s3_client.delete_file(result['metadata_file'])
        
        if sample_pdf and sample_pdf != 'test_article.pdf':
            os.unlink(sample_pdf)
        
        print("\n🎉 Document processing test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error during document processing test: {e}")
        return False

if __name__ == "__main__":
    # Note: This requires AWS credentials and may incur small charges for Textract usage
    print("⚠️  This test will use AWS Textract and may incur small charges.")
    print("⚠️  Make sure your AWS credentials are configured in .env file.")
    
    response = input("Continue with the test? (y/N): ")
    if response.lower() == 'y':
        test_document_processing()
    else:
        print("Test cancelled.")