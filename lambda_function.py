import json
import urllib.parse
import logging
from datetime import datetime
from typing import List, Dict, Any

from src.document_processor import DocumentProcessor
from src.textract_models import ProcessingResult, ProcessingStatus

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def lambda_handler(event, context) -> Dict[str, Any]:
    """
    Enhanced AWS Lambda function to process PDF uploads to S3
    Triggered by S3 PUT events in the input-articles/ folder
    
    Args:
        event: S3 event data
        context: Lambda context
        
    Returns:
        HTTP response with processing results
    """
    
    start_time = datetime.utcnow()
    processing_results: List[ProcessingResult] = []
    
    try:
        logger.info(f"Lambda function started at {start_time.isoformat()}")
        logger.info(f"Event received: {json.dumps(event, indent=2)}")
        
        # Validate event structure
        if not event or 'Records' not in event:
            logger.warning("Invalid event structure - no Records found")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Invalid event structure - no Records found'})
            }
        
        records = event.get('Records', [])
        logger.info(f"Processing {len(records)} S3 event records")
        
        if not records:
            logger.info("No records to process")
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'No records to process'})
            }
        
        # Initialize document processor
        processor = DocumentProcessor()
        
        # Process each S3 event record
        for i, record in enumerate(event.get('Records', [])):
            try:
                # Get bucket and object key from the event
                bucket = record['s3']['bucket']['name']
                key = urllib.parse.unquote_plus(record['s3']['object']['key'], encoding='utf-8')
                
                logger.info(f"Record {i+1}: Processing S3 event for bucket={bucket}, key={key}")
                
                # Validate event is for correct folder and file type
                if not _should_process_file(key):
                    logger.info(f"Skipping file {key} - not in input folder or not PDF")
                    continue
                
                logger.info(f"Processing PDF: {key}")
                
                # Process the PDF with enhanced error handling
                result = processor.process_uploaded_pdf(key)
                processing_results.append(result)
                
                # Log result summary
                if result.status == ProcessingStatus.COMPLETED:
                    logger.info(f"✅ Successfully processed {key} -> {result.text_file_key}")
                else:
                    logger.error(f"❌ Failed to process {key}: {result.error_message}")
                
            except Exception as record_error:
                logger.error(f"Error processing record {i+1}: {str(record_error)}", exc_info=True)
                
                # Create error result for this record
                error_result = ProcessingResult(
                    status=ProcessingStatus.FAILED,
                    original_file=key if 'key' in locals() else 'unknown',
                    error_message=f"Record processing error: {str(record_error)}",
                    processing_timestamp=start_time
                )
                processing_results.append(error_result)
        
        # Calculate summary statistics
        total_processed = len(processing_results)
        successful = sum(1 for r in processing_results if r.status == ProcessingStatus.COMPLETED)
        failed = total_processed - successful
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        logger.info(f"Lambda processing completed in {processing_time:.2f}s: "
                   f"{successful} successful, {failed} failed out of {total_processed} total")
        
        # Return success response with detailed results
        response_body = {
            'message': f'Processed {total_processed} document(s): {successful} successful, {failed} failed',
            'summary': {
                'total_processed': total_processed,
                'successful': successful,
                'failed': failed,
                'processing_time_seconds': processing_time
            },
            'results': [_serialize_processing_result(result) for result in processing_results],
            'timestamp': start_time.isoformat()
        }
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps(response_body, indent=2)
        }
        
    except Exception as e:
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        error_message = f"Lambda function error after {processing_time:.2f}s: {str(e)}"
        
        logger.error(error_message, exc_info=True)
        
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'error': str(e),
                'message': 'Failed to process PDF upload(s)',
                'processing_time_seconds': processing_time,
                'timestamp': start_time.isoformat()
            }, indent=2)
        }

def _should_process_file(file_key: str) -> bool:
    """
    Determine if a file should be processed based on its key
    
    Args:
        file_key: S3 object key
        
    Returns:
        True if file should be processed
    """
    logger.info(f"Evaluating file for processing: {file_key}")
    
    # Check if file is in the correct input folder
    if not file_key.startswith('input-articles/'):
        logger.info(f"Skipping {file_key}: not in input-articles/ folder")
        return False
    
    # Check if file is a PDF
    if not file_key.lower().endswith('.pdf'):
        logger.info(f"Skipping {file_key}: not a PDF file (extension: {file_key.split('.')[-1] if '.' in file_key else 'none'})")
        return False
    
    # Skip hidden files or system files
    filename = file_key.split('/')[-1]
    if filename.startswith('.') or filename.startswith('_'):
        logger.info(f"Skipping {file_key}: hidden or system file")
        return False
    
    logger.info(f"✅ File {file_key} approved for processing")
    return True

def _serialize_processing_result(result: ProcessingResult) -> Dict[str, Any]:
    """
    Serialize ProcessingResult for JSON response
    
    Args:
        result: ProcessingResult object
        
    Returns:
        Dictionary representation suitable for JSON serialization
    """
    serialized = {
        'status': result.status.value,
        'original_file': result.original_file,
        'processing_timestamp': result.processing_timestamp.isoformat()
    }
    
    if result.text_file_key:
        serialized['text_file_key'] = result.text_file_key
    
    if result.metadata_file_key:
        serialized['metadata_file_key'] = result.metadata_file_key
    
    if result.error_message:
        serialized['error_message'] = result.error_message
    
    if result.extraction_result:
        serialized['extraction_summary'] = {
            'character_count': result.extraction_result.character_count,
            'word_count': result.extraction_result.word_count,
            'page_count': result.extraction_result.page_count,
            'processing_time': result.extraction_result.processing_time,
            'extraction_method': result.extraction_result.extraction_method.value,
            'average_confidence': result.extraction_result.confidence_stats.average_confidence,
            'is_high_quality': result.extraction_result.is_high_quality
        }
    
    return serialized