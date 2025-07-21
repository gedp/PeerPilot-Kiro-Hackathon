#!/usr/bin/env python3
"""
Monitor and test the automated PDF processing pipeline for PeerPilot
"""

import os
import time
import tempfile
from pathlib import Path
from src.s3_client import S3Client
from src.document_processor import DocumentProcessor

class ProcessingMonitor:
    def __init__(self):
        self.s3_client = S3Client()
        self.processor = DocumentProcessor()
        self.bucket_name = self.s3_client.bucket_name
    
    def create_test_pdf_content(self):
        """Create a simple test PDF content as text (for demonstration)"""
        return """
# Test Scientific Article

## Abstract
This is a test article for the PeerPilot system. The abstract contains important information about the research methodology and findings.

## Introduction
Scientific research requires proper peer review processes. This test document demonstrates the automated ingestion capabilities of the PeerPilot system.

## Methodology
The methodology section describes the approach used in this research study.

## Results
Key findings and results are presented in this section with detailed analysis.

## Conclusion
The conclusion summarizes the main contributions and future work directions.

## References
1. Sample Reference 1
2. Sample Reference 2
"""
    
    def upload_test_pdf(self, filename="test_article.pdf"):
        """Upload a test PDF to trigger the processing pipeline"""
        print(f"📤 Uploading test PDF: {filename}")
        
        # Create a temporary text file (simulating PDF content)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
            temp_file.write(self.create_test_pdf_content())
            temp_file_path = temp_file.name
        
        try:
            # Upload to the input folder
            s3_key = f"articulos-entrada/{filename}"
            success = self.s3_client.upload_file(temp_file_path, s3_key)
            
            if success:
                print(f"✅ Test file uploaded to s3://{self.bucket_name}/{s3_key}")
                return s3_key
            else:
                print("❌ Failed to upload test file")
                return None
        finally:
            os.unlink(temp_file_path)
    
    def check_processing_status(self, original_filename, max_wait_time=300):
        """Monitor the processing status of an uploaded file"""
        base_name = Path(original_filename).stem
        text_key = f"processed-articles/{base_name}.txt"
        metadata_key = f"processed-articles/{base_name}_metadata.json"
        error_key = f"processed-articles/{base_name}_error.json"
        
        print(f"🔍 Monitoring processing status for: {original_filename}")
        print(f"   Expected output: {text_key}")
        
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            # Check for successful processing
            files = self.s3_client.list_files("processed-articles/")
            
            if text_key in files:
                print(f"✅ Processing completed! Text file created: {text_key}")
                
                # Download and display metadata if available
                if metadata_key in files:
                    self._display_metadata(metadata_key)
                
                return "completed"
            
            # Check for error
            if error_key in files:
                print(f"❌ Processing failed! Error file created: {error_key}")
                self._display_error(error_key)
                return "failed"
            
            print(f"⏳ Still processing... ({int(time.time() - start_time)}s elapsed)")
            time.sleep(10)
        
        print(f"⏰ Timeout reached ({max_wait_time}s). Processing may still be in progress.")
        return "timeout"
    
    def _display_metadata(self, metadata_key):
        """Download and display processing metadata"""
        import json
        import tempfile
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            temp_file_path = temp_file.name
        
        try:
            if self.s3_client.download_file(metadata_key, temp_file_path):
                with open(temp_file_path, 'r') as f:
                    metadata = json.load(f)
                
                print("\n📊 Processing Metadata:")
                print(f"   Original file: {metadata.get('original_file')}")
                print(f"   Extraction time: {metadata.get('extraction_timestamp')}")
                print(f"   Text length: {metadata.get('text_length')} characters")
                print(f"   Method: {metadata.get('extraction_method')}")
                print(f"   Status: {metadata.get('status')}")
        finally:
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
    
    def _display_error(self, error_key):
        """Download and display error information"""
        import json
        import tempfile
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            temp_file_path = temp_file.name
        
        try:
            if self.s3_client.download_file(error_key, temp_file_path):
                with open(temp_file_path, 'r') as f:
                    error_data = json.load(f)
                
                print("\n❌ Error Details:")
                print(f"   Original file: {error_data.get('original_file')}")
                print(f"   Error: {error_data.get('error')}")
                print(f"   Timestamp: {error_data.get('timestamp')}")
        finally:
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
    
    def list_all_processed_files(self):
        """List all files in the processing pipeline"""
        print("\n📋 Current S3 Bucket Contents:")
        
        folders = ["articulos-entrada/", "processed-articles/"]
        
        for folder in folders:
            files = self.s3_client.list_files(folder)
            print(f"\n📁 {folder}")
            if files:
                for file in files:
                    print(f"   📄 {file}")
            else:
                print("   (empty)")
    
    def test_local_processing(self, pdf_key):
        """Test the document processor locally (without Lambda)"""
        print(f"\n🧪 Testing local processing for: {pdf_key}")
        
        try:
            result = self.processor.process_uploaded_pdf(pdf_key)
            print(f"✅ Local processing result: {result}")
            return result
        except Exception as e:
            print(f"❌ Local processing failed: {e}")
            return None
    
    def cleanup_test_files(self):
        """Clean up test files from S3"""
        print("\n🧹 Cleaning up test files...")
        
        test_files = [
            "articulos-entrada/test_article.pdf",
            "processed-articles/test_article.txt",
            "processed-articles/test_article_metadata.json",
            "processed-articles/test_article_error.json"
        ]
        
        for file_key in test_files:
            try:
                self.s3_client.delete_file(file_key)
                print(f"   🗑️ Deleted: {file_key}")
            except:
                pass  # File might not exist

def main():
    """Main monitoring and testing function"""
    print("🚀 PeerPilot Processing Pipeline Monitor")
    print("=" * 50)
    
    monitor = ProcessingMonitor()
    
    # List current files
    monitor.list_all_processed_files()
    
    # Upload test file
    test_filename = "test_article.pdf"
    uploaded_key = monitor.upload_test_pdf(test_filename)
    
    if uploaded_key:
        # Test local processing first
        print("\n" + "="*50)
        print("🧪 TESTING LOCAL PROCESSING")
        print("="*50)
        local_result = monitor.test_local_processing(uploaded_key)
        
        if local_result and local_result.get("status") == "success":
            print("\n✅ Local processing successful!")
            print("   Your document processor is working correctly.")
            print("   For serverless processing, deploy the Lambda function.")
        else:
            print("\n❌ Local processing failed!")
            print("   Check your AWS credentials and Textract permissions.")
    
    # Show final state
    print("\n" + "="*50)
    print("📋 FINAL BUCKET STATE")
    print("="*50)
    monitor.list_all_processed_files()
    
    # Cleanup option
    cleanup = input("\n🧹 Clean up test files? (y/N): ").lower().strip()
    if cleanup == 'y':
        monitor.cleanup_test_files()
        print("✅ Cleanup completed!")

if __name__ == "__main__":
    main()