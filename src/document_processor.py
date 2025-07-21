import os
import json
from pathlib import Path
from src.s3_client import S3Client
from src.textract_client import TextractClient
import logging

logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(self):
        self.s3_client = S3Client()
        self.textract_client = TextractClient()
        self.bucket_name = self.s3_client.bucket_name
    
    def process_uploaded_pdf(self, pdf_key):
        """
        Main processing function for uploaded PDFs
        """
        try:
            logger.info(f"Processing PDF: {pdf_key}")
            
            # Extract text using Textract
            extracted_text = self._extract_text_with_fallback(pdf_key)
            
            # Generate output file names
            base_name = Path(pdf_key).stem  # Remove .pdf extension
            text_key = f"processed-articles/{base_name}.txt"
            metadata_key = f"processed-articles/{base_name}_metadata.json"
            
            # Save extracted text to S3
            self._save_text_to_s3(text_key, extracted_text)
            
            # Create and save metadata
            metadata = self.textract_client.create_extraction_metadata(
                pdf_key, len(extracted_text), "textract"
            )
            self._save_metadata_to_s3(metadata_key, metadata)
            
            logger.info(f"Successfully processed {pdf_key} -> {text_key}")
            
            return {
                "status": "success",
                "original_file": pdf_key,
                "text_file": text_key,
                "metadata_file": metadata_key,
                "text_length": len(extracted_text)
            }
            
        except Exception as e:
            logger.error(f"Failed to process {pdf_key}: {e}")
            
            # Save error metadata
            error_metadata = {
                "original_file": pdf_key,
                "status": "failed",
                "error": str(e),
                "timestamp": self.textract_client.create_extraction_metadata(pdf_key, 0, "failed")["extraction_timestamp"]
            }
            
            base_name = Path(pdf_key).stem
            error_key = f"processed-articles/{base_name}_error.json"
            self._save_metadata_to_s3(error_key, error_metadata)
            
            return {
                "status": "error",
                "original_file": pdf_key,
                "error": str(e)
            }
    
    def _extract_text_with_fallback(self, pdf_key):
        """
        Extract text with fallback from async to sync method
        """
        try:
            # Try async method first (better for larger documents)
            return self.textract_client.extract_text_from_pdf(self.bucket_name, pdf_key)
        except Exception as e:
            logger.warning(f"Async extraction failed for {pdf_key}, trying sync method: {e}")
            try:
                # Fallback to sync method
                return self.textract_client.extract_text_sync(self.bucket_name, pdf_key)
            except Exception as sync_error:
                logger.error(f"Both extraction methods failed for {pdf_key}: {sync_error}")
                raise sync_error
    
    def _save_text_to_s3(self, text_key, text_content):
        """Save extracted text to S3"""
        import tempfile
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
            temp_file.write(text_content)
            temp_file_path = temp_file.name
        
        try:
            success = self.s3_client.upload_file(temp_file_path, text_key)
            if not success:
                raise Exception("Failed to upload text file to S3")
        finally:
            os.unlink(temp_file_path)
    
    def _save_metadata_to_s3(self, metadata_key, metadata):
        """Save metadata to S3"""
        import tempfile
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            json.dump(metadata, temp_file, indent=2)
            temp_file_path = temp_file.name
        
        try:
            success = self.s3_client.upload_file(temp_file_path, metadata_key)
            if not success:
                raise Exception("Failed to upload metadata file to S3")
        finally:
            os.unlink(temp_file_path)
    
    def list_processed_articles(self):
        """List all processed articles"""
        return self.s3_client.list_files("processed-articles/")
    
    def get_processed_text(self, article_name):
        """Get processed text for a specific article"""
        text_key = f"processed-articles/{article_name}.txt"
        
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
            temp_file_path = temp_file.name
        
        try:
            if self.s3_client.download_file(text_key, temp_file_path):
                with open(temp_file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            return None
        finally:
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)