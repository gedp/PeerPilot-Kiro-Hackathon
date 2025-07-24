import boto3
import json
import time
import os
from datetime import datetime
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional
import logging

from .textract_models import (
    TextExtractionResult, ConfidenceStats, ExtractionMethod, ValidationResult,
    ProcessingConfig, TextractError, DocumentValidationError, 
    ExtractionTimeoutError, UnsupportedDocumentError, TextractServiceError,
    ExtractionQualityError
)

load_dotenv()
logger = logging.getLogger(__name__)

class TextractClient:
    """
    Enhanced Amazon Textract client with intelligent method selection and robust error handling
    """
    
    def __init__(self, region_name: Optional[str] = None):
        """
        Initialize Textract client
        
        Args:
            region_name: AWS region name (defaults to environment variable or us-east-1)
        """
        self.region = region_name or os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        
        try:
            self.textract = boto3.client('textract', region_name=self.region)
            self.s3 = boto3.client('s3', region_name=self.region)
            logger.info(f"TextractClient initialized for region: {self.region}")
        except Exception as e:
            raise TextractError(f"Failed to initialize Textract client: {str(e)}", original_error=e)
    
    def extract_text_from_document(self, bucket_name: str, document_key: str) -> TextExtractionResult:
        """
        Main method to extract text from a document with intelligent method selection
        
        Args:
            bucket_name: S3 bucket name
            document_key: S3 object key for the document
            
        Returns:
            TextExtractionResult with extracted text and metadata
            
        Raises:
            DocumentValidationError: If document validation fails
            TextractServiceError: If Textract service fails
            ExtractionTimeoutError: If extraction times out
        """
        start_time = time.time()
        
        try:
            # Validate document first
            validation = self._validate_document(bucket_name, document_key)
            if not validation.is_valid:
                raise DocumentValidationError(
                    f"Document validation failed: {validation.error_message}",
                    error_code="VALIDATION_FAILED"
                )
            
            # Determine extraction method
            use_async = self._should_use_async_extraction(bucket_name, document_key, validation.file_size)
            
            if use_async:
                logger.info(f"Using async extraction for {document_key}")
                result = self._extract_text_async(bucket_name, document_key)
            else:
                logger.info(f"Using sync extraction for {document_key}")
                result = self._extract_text_sync(bucket_name, document_key)
            
            processing_time = time.time() - start_time
            
            # Create comprehensive result
            extraction_result = TextExtractionResult(
                text_content=result['text'],
                confidence_stats=result['confidence_stats'],
                extraction_method=result['method'],
                processing_time=processing_time,
                page_count=result['page_count'],
                character_count=len(result['text']),
                word_count=len(result['text'].split()),
                metadata={
                    'original_file': document_key,
                    'file_size': validation.file_size,
                    'textract_job_id': result.get('job_id'),
                    'blocks_processed': result['confidence_stats'].total_blocks
                },
                extraction_timestamp=datetime.utcnow()
            )
            
            # Validate extraction quality
            if not extraction_result.is_high_quality:
                logger.warning(f"Low quality extraction for {document_key}: "
                             f"avg_confidence={extraction_result.confidence_stats.average_confidence:.2f}")
            
            logger.info(f"Successfully extracted {len(result['text'])} characters from {document_key} "
                       f"in {processing_time:.2f}s using {result['method'].value} method")
            
            return extraction_result
            
        except (DocumentValidationError, TextractServiceError, ExtractionTimeoutError):
            raise
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'UNKNOWN')
            raise TextractServiceError(
                f"AWS Textract error for {document_key}: {str(e)}",
                error_code=error_code,
                original_error=e
            )
        except Exception as e:
            raise TextractError(
                f"Unexpected error extracting text from {document_key}: {str(e)}",
                error_code="UNEXPECTED_ERROR",
                original_error=e
            )
    
    def _validate_document(self, bucket_name: str, document_key: str) -> ValidationResult:
        """
        Validate document before processing
        
        Args:
            bucket_name: S3 bucket name
            document_key: S3 object key
            
        Returns:
            ValidationResult with validation status and details
        """
        try:
            # Get object metadata
            response = self.s3.head_object(Bucket=bucket_name, Key=document_key)
            file_size = response['ContentLength']
            
            # Check file extension
            if not any(document_key.lower().endswith(ext) for ext in ProcessingConfig.SUPPORTED_EXTENSIONS):
                return ValidationResult(
                    is_valid=False,
                    file_size=file_size,
                    file_format="unsupported",
                    error_message=f"Unsupported file format. Supported: {ProcessingConfig.SUPPORTED_EXTENSIONS}"
                )
            
            # Check file size
            max_size = ProcessingConfig.MAX_DOCUMENT_SIZE_MB * 1024 * 1024
            if file_size > max_size:
                return ValidationResult(
                    is_valid=False,
                    file_size=file_size,
                    file_format="pdf",
                    error_message=f"File size {file_size / 1024 / 1024:.2f}MB exceeds maximum {ProcessingConfig.MAX_DOCUMENT_SIZE_MB}MB"
                )
            
            warnings = []
            if file_size > ProcessingConfig.SYNC_SIZE_LIMIT_MB * 1024 * 1024:
                warnings.append("Large file will use asynchronous processing")
            
            return ValidationResult(
                is_valid=True,
                file_size=file_size,
                file_format="pdf",
                warnings=warnings
            )
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            http_status = e.response.get('ResponseMetadata', {}).get('HTTPStatusCode', 0)
            
            # Handle 404 Not Found errors (can be NoSuchKey, NoSuchBucket, or HTTP 404)
            if error_code in ['NoSuchKey', 'NoSuchBucket', '404'] or http_status == 404:
                return ValidationResult(
                    is_valid=False,
                    file_size=0,
                    file_format="unknown",
                    error_message=f"Document not found: {document_key}"
                )
            
            # Handle access denied errors
            if error_code in ['AccessDenied', 'Forbidden'] or http_status == 403:
                return ValidationResult(
                    is_valid=False,
                    file_size=0,
                    file_format="unknown",
                    error_message=f"Access denied to document: {document_key}"
                )
            
            # For other errors, re-raise to be handled by calling code
            raise
    
    def _should_use_async_extraction(self, bucket_name: str, document_key: str, file_size: int) -> bool:
        """
        Determine whether to use asynchronous extraction
        
        Args:
            bucket_name: S3 bucket name
            document_key: S3 object key
            file_size: File size in bytes
            
        Returns:
            True if async extraction should be used
        """
        # Use async for large files
        size_limit = ProcessingConfig.SYNC_SIZE_LIMIT_MB * 1024 * 1024
        if file_size >= size_limit:
            return True
        
        # For smaller files, use sync by default
        return False
    
    def _extract_text_async(self, bucket_name: str, document_key: str) -> Dict[str, Any]:
        """
        Extract text using asynchronous Textract
        
        Args:
            bucket_name: S3 bucket name
            document_key: S3 object key
            
        Returns:
            Dictionary with extracted text and metadata
        """
        try:
            # Start document text detection job
            response = self.textract.start_document_text_detection(
                DocumentLocation={
                    'S3Object': {
                        'Bucket': bucket_name,
                        'Name': document_key
                    }
                }
            )
            
            job_id = response['JobId']
            logger.info(f"Started async Textract job {job_id} for {document_key}")
            
            # Wait for job completion
            result = self._wait_for_job_completion(job_id, ProcessingConfig.MAX_ASYNC_WAIT_TIME)
            
            # Extract text from all pages
            all_blocks = []
            next_token = None
            
            while True:
                if next_token:
                    response = self.textract.get_document_text_detection(
                        JobId=job_id,
                        NextToken=next_token
                    )
                else:
                    response = self.textract.get_document_text_detection(JobId=job_id)
                
                all_blocks.extend(response.get('Blocks', []))
                next_token = response.get('NextToken')
                if not next_token:
                    break
            
            # Extract text and calculate statistics
            text_content = self._extract_text_from_blocks(all_blocks)
            confidence_stats = ConfidenceStats.from_blocks(all_blocks)
            page_count = len(set(block.get('Page', 1) for block in all_blocks if 'Page' in block))
            
            return {
                'text': text_content,
                'confidence_stats': confidence_stats,
                'method': ExtractionMethod.ASYNC,
                'page_count': max(page_count, 1),
                'job_id': job_id
            }
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'UNKNOWN')
            raise TextractServiceError(
                f"Async extraction failed for {document_key}: {str(e)}",
                error_code=error_code,
                original_error=e
            )
    
    def _extract_text_sync(self, bucket_name: str, document_key: str) -> Dict[str, Any]:
        """
        Extract text using synchronous Textract
        
        Args:
            bucket_name: S3 bucket name
            document_key: S3 object key
            
        Returns:
            Dictionary with extracted text and metadata
        """
        try:
            # Get the document from S3
            response = self.s3.get_object(Bucket=bucket_name, Key=document_key)
            document_content = response['Body'].read()
            
            # Use synchronous text detection
            response = self.textract.detect_document_text(
                Document={'Bytes': document_content}
            )
            
            blocks = response.get('Blocks', [])
            
            # Extract text and calculate statistics
            text_content = self._extract_text_from_blocks(blocks)
            confidence_stats = ConfidenceStats.from_blocks(blocks)
            
            return {
                'text': text_content,
                'confidence_stats': confidence_stats,
                'method': ExtractionMethod.SYNC,
                'page_count': 1,  # Sync is typically single page
                'job_id': None
            }
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'UNKNOWN')
            raise TextractServiceError(
                f"Sync extraction failed for {document_key}: {str(e)}",
                error_code=error_code,
                original_error=e
            )
    
    def _wait_for_job_completion(self, job_id: str, max_wait_time: int = 300) -> Dict[str, Any]:
        """
        Wait for asynchronous Textract job to complete
        
        Args:
            job_id: Textract job ID
            max_wait_time: Maximum time to wait in seconds
            
        Returns:
            Final job response
            
        Raises:
            ExtractionTimeoutError: If job times out
            TextractServiceError: If job fails
        """
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            try:
                response = self.textract.get_document_text_detection(JobId=job_id)
                status = response['JobStatus']
                
                if status == 'SUCCEEDED':
                    logger.info(f"Textract job {job_id} completed successfully")
                    return response
                elif status == 'FAILED':
                    error_msg = response.get('StatusMessage', 'Unknown error')
                    raise TextractServiceError(
                        f"Textract job {job_id} failed: {error_msg}",
                        error_code="JOB_FAILED"
                    )
                elif status in ['IN_PROGRESS', 'PARTIAL_SUCCESS']:
                    logger.debug(f"Job {job_id} status: {status}, waiting...")
                    time.sleep(ProcessingConfig.POLL_INTERVAL)
                else:
                    logger.warning(f"Unknown job status for {job_id}: {status}")
                    time.sleep(ProcessingConfig.POLL_INTERVAL)
                    
            except ClientError as e:
                raise TextractServiceError(
                    f"Error checking job status for {job_id}: {str(e)}",
                    error_code=e.response.get('Error', {}).get('Code', 'UNKNOWN'),
                    original_error=e
                )
        
        raise ExtractionTimeoutError(
            f"Textract job {job_id} timed out after {max_wait_time} seconds",
            error_code="JOB_TIMEOUT"
        )
    
    def _extract_text_from_blocks(self, blocks: List[Dict[str, Any]]) -> str:
        """
        Extract text content from Textract blocks
        
        Args:
            blocks: List of Textract block objects
            
        Returns:
            Extracted text as string
        """
        text_lines = []
        
        # Sort blocks by page and geometry for proper text order
        line_blocks = [block for block in blocks if block.get('BlockType') == 'LINE']
        
        # Sort by page, then by top position, then by left position
        line_blocks.sort(key=lambda b: (
            b.get('Page', 1),
            b.get('Geometry', {}).get('BoundingBox', {}).get('Top', 0),
            b.get('Geometry', {}).get('BoundingBox', {}).get('Left', 0)
        ))
        
        for block in line_blocks:
            if 'Text' in block:
                text_lines.append(block['Text'])
        
        return '\n'.join(text_lines)