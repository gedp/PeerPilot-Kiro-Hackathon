import os
import json
import tempfile
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any
import logging

from .s3_client import S3Client
from .textract_client import TextractClient
from .textract_models import (
    ProcessingResult, ProcessingStatus, ProcessedDocument, 
    TextExtractionResult, ProcessingConfig, TextractError,
    DocumentValidationError, ExtractionTimeoutError, TextractServiceError,
    ConfidenceStats, ExtractionMethod
)

logger = logging.getLogger(__name__)

class DocumentProcessor:
    """
    Enhanced document processor with comprehensive error handling and retry logic
    """
    
    def __init__(self, bucket_name: Optional[str] = None):
        """
        Initialize document processor
        
        Args:
            bucket_name: S3 bucket name (defaults to S3Client default)
        """
        self.s3_client = S3Client(bucket_name=bucket_name)
        self.textract_client = TextractClient()
        self.bucket_name = self.s3_client.bucket_name
        
        logger.info(f"DocumentProcessor initialized for bucket: {self.bucket_name}")
    
    def process_uploaded_pdf(self, pdf_key: str) -> ProcessingResult:
        """
        Main processing function for uploaded PDFs with comprehensive error handling
        
        Args:
            pdf_key: S3 key for the PDF document
            
        Returns:
            ProcessingResult with processing status and details
        """
        start_time = datetime.utcnow()
        
        try:
            logger.info(f"Starting processing for PDF: {pdf_key}")
            
            # Validate document path
            if not pdf_key.startswith(ProcessingConfig.INPUT_PREFIX):
                logger.warning(f"Document {pdf_key} not in expected input folder")
            
            # Extract text with retry logic
            extraction_result = self._extract_text_with_retry(pdf_key)
            
            # Save extraction results
            text_key, metadata_key = self._save_extraction_results(pdf_key, extraction_result)
            
            # Create processing result
            result = ProcessingResult(
                status=ProcessingStatus.COMPLETED,
                original_file=pdf_key,
                text_file_key=text_key,
                metadata_file_key=metadata_key,
                extraction_result=extraction_result,
                processing_timestamp=start_time
            )
            
            logger.info(f"Successfully processed {pdf_key} -> {text_key} "
                       f"({extraction_result.character_count} chars, "
                       f"{extraction_result.processing_time:.2f}s)")
            
            return result
            
        except DocumentValidationError as e:
            logger.error(f"Document validation failed for {pdf_key}: {e}")
            return self._create_error_result(pdf_key, ProcessingStatus.FAILED, str(e), start_time)
            
        except ExtractionTimeoutError as e:
            logger.error(f"Extraction timeout for {pdf_key}: {e}")
            return self._create_error_result(pdf_key, ProcessingStatus.TIMEOUT, str(e), start_time)
            
        except TextractServiceError as e:
            logger.error(f"Textract service error for {pdf_key}: {e}")
            return self._create_error_result(pdf_key, ProcessingStatus.FAILED, str(e), start_time)
            
        except Exception as e:
            logger.error(f"Unexpected error processing {pdf_key}: {e}", exc_info=True)
            return self._create_error_result(pdf_key, ProcessingStatus.FAILED, 
                                           f"Unexpected error: {str(e)}", start_time)
    
    def _extract_text_with_retry(self, pdf_key: str) -> TextExtractionResult:
        """
        Extract text with retry logic and fallback methods
        
        Args:
            pdf_key: S3 key for the PDF document
            
        Returns:
            TextExtractionResult with extracted text and metadata
            
        Raises:
            TextractError: If all extraction attempts fail
        """
        last_error = None
        
        for attempt in range(ProcessingConfig.RETRY_ATTEMPTS):
            try:
                logger.info(f"Text extraction attempt {attempt + 1}/{ProcessingConfig.RETRY_ATTEMPTS} for {pdf_key}")
                
                # Use the enhanced TextractClient method
                result = self.textract_client.extract_text_from_document(self.bucket_name, pdf_key)
                
                logger.info(f"Successfully extracted text on attempt {attempt + 1}")
                return result
                
            except (DocumentValidationError, ExtractionTimeoutError) as e:
                # Don't retry validation errors or timeouts
                logger.error(f"Non-retryable error for {pdf_key}: {e}")
                raise
                
            except TextractError as e:
                last_error = e
                logger.warning(f"Extraction attempt {attempt + 1} failed for {pdf_key}: {e}")
                
                if attempt < ProcessingConfig.RETRY_ATTEMPTS - 1:
                    logger.info(f"Retrying in {ProcessingConfig.RETRY_DELAY} seconds...")
                    import time
                    time.sleep(ProcessingConfig.RETRY_DELAY)
                else:
                    logger.error(f"All {ProcessingConfig.RETRY_ATTEMPTS} extraction attempts failed for {pdf_key}")
        
        # If we get here, all attempts failed
        raise last_error or TextractError(f"Failed to extract text from {pdf_key} after {ProcessingConfig.RETRY_ATTEMPTS} attempts")
    
    def _save_extraction_results(self, pdf_key: str, extraction_result: TextExtractionResult) -> tuple[str, str]:
        """
        Save extraction results to S3
        
        Args:
            pdf_key: Original PDF S3 key
            extraction_result: Text extraction result
            
        Returns:
            Tuple of (text_key, metadata_key) for saved files
        """
        # Generate output keys
        text_key = ProcessingConfig.get_text_output_key(pdf_key)
        metadata_key = ProcessingConfig.get_metadata_output_key(pdf_key)
        
        try:
            # Save extracted text
            self._save_text_to_s3(text_key, extraction_result.text_content)
            
            # Save extraction metadata
            self._save_metadata_to_s3(metadata_key, extraction_result.to_dict())
            
            logger.info(f"Saved extraction results: {text_key}, {metadata_key}")
            return text_key, metadata_key
            
        except Exception as e:
            logger.error(f"Failed to save extraction results for {pdf_key}: {e}")
            raise TextractError(f"Failed to save extraction results: {str(e)}", original_error=e)
    
    def _create_error_result(self, pdf_key: str, status: ProcessingStatus, 
                           error_message: str, start_time: datetime) -> ProcessingResult:
        """
        Create error result and save error information
        
        Args:
            pdf_key: Original PDF S3 key
            status: Processing status
            error_message: Error message
            start_time: Processing start time
            
        Returns:
            ProcessingResult with error information
        """
        try:
            # Save error information to S3
            error_key = ProcessingConfig.get_error_output_key(pdf_key)
            error_data = {
                "original_file": pdf_key,
                "status": status.value,
                "error_message": error_message,
                "processing_timestamp": start_time.isoformat(),
                "error_timestamp": datetime.utcnow().isoformat()
            }
            
            self._save_metadata_to_s3(error_key, error_data)
            logger.info(f"Saved error information to {error_key}")
            
        except Exception as save_error:
            logger.error(f"Failed to save error information for {pdf_key}: {save_error}")
        
        return ProcessingResult(
            status=status,
            original_file=pdf_key,
            error_message=error_message,
            processing_timestamp=start_time
        )
    
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
    
    def list_processed_documents(self) -> List[ProcessedDocument]:
        """
        List all processed documents with their metadata
        
        Returns:
            List of ProcessedDocument objects
        """
        try:
            # Get all text files from extracted-texts folder
            text_files = self.s3_client.list_files(ProcessingConfig.OUTPUT_TEXT_PREFIX)
            processed_docs = []
            
            for text_file in text_files:
                if text_file.endswith(ProcessingConfig.TEXT_OUTPUT_EXTENSION):
                    # Extract document name
                    base_name = Path(text_file).stem
                    
                    # Try to get metadata
                    metadata_key = ProcessingConfig.get_metadata_output_key(f"{ProcessingConfig.INPUT_PREFIX}{base_name}.pdf")
                    
                    try:
                        # Get file info from S3
                        response = self.s3_client.s3_client.head_object(
                            Bucket=self.bucket_name, 
                            Key=text_file
                        )
                        
                        processed_doc = ProcessedDocument(
                            name=base_name,
                            original_key=f"{ProcessingConfig.INPUT_PREFIX}{base_name}.pdf",
                            text_key=text_file,
                            metadata_key=metadata_key,
                            processing_date=response['LastModified'],
                            status=ProcessingStatus.COMPLETED,
                            file_size=response['ContentLength'],
                            processing_time=0.0  # Would need to get from metadata
                        )
                        processed_docs.append(processed_doc)
                        
                    except Exception as e:
                        logger.warning(f"Could not get metadata for {text_file}: {e}")
                        continue
            
            return processed_docs
            
        except Exception as e:
            logger.error(f"Failed to list processed documents: {e}")
            return []
    
    def get_extraction_result(self, document_name: str) -> Optional[TextExtractionResult]:
        """
        Get extraction result for a specific document
        
        Args:
            document_name: Base name of the document (without extension)
            
        Returns:
            TextExtractionResult if found, None otherwise
        """
        try:
            # Generate metadata key
            original_key = f"{ProcessingConfig.INPUT_PREFIX}{document_name}.pdf"
            metadata_key = ProcessingConfig.get_metadata_output_key(original_key)
            
            # Download metadata file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                temp_file_path = temp_file.name
            
            try:
                if self.s3_client.download_file(metadata_key, temp_file_path):
                    with open(temp_file_path, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    
                    # Reconstruct TextExtractionResult from metadata
                    # This is a simplified reconstruction - in practice you might want to store the full object
                    return TextExtractionResult(
                        text_content="",  # Would need to load from text file
                        confidence_stats=ConfidenceStats(**metadata.get('confidence_stats', {})),
                        extraction_method=ExtractionMethod(metadata.get('extraction_method', 'sync')),
                        processing_time=metadata.get('processing_time', 0.0),
                        page_count=metadata.get('page_count', 1),
                        character_count=metadata.get('character_count', 0),
                        word_count=metadata.get('word_count', 0),
                        metadata=metadata.get('metadata', {}),
                        extraction_timestamp=datetime.fromisoformat(metadata.get('extraction_timestamp', datetime.utcnow().isoformat()))
                    )
                
                return None
                
            finally:
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    
        except Exception as e:
            logger.error(f"Failed to get extraction result for {document_name}: {e}")
            return None
    
    def get_processed_text(self, document_name: str) -> Optional[str]:
        """
        Get processed text for a specific document
        
        Args:
            document_name: Base name of the document (without extension)
            
        Returns:
            Extracted text content if found, None otherwise
        """
        try:
            # Generate text key
            original_key = f"{ProcessingConfig.INPUT_PREFIX}{document_name}.pdf"
            text_key = ProcessingConfig.get_text_output_key(original_key)
            
            # Download text file
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
                    
        except Exception as e:
            logger.error(f"Failed to get processed text for {document_name}: {e}")
            return None