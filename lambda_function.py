import json
import urllib.parse
import logging
from src.document_processor import DocumentProcessor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def lambda_handler(event, context):
    """
    AWS Lambda function to process PDF uploads to S3
    Triggered by S3 PUT events in the articulos-entrada/ folder
    """
    
    try:
        # Initialize document processor
        processor = DocumentProcessor()
        
        results = []
        
        # Process each S3 event record
        for record in event['Records']:
            # Get bucket and object key from the event
            bucket = record['s3']['bucket']['name']
            key = urllib.parse.unquote_plus(record['s3']['object']['key'], encoding='utf-8')
            
            logger.info(f"Processing S3 event: bucket={bucket}, key={key}")
            
            # Only process PDF files in the articulos-entrada folder
            if key.startswith('articulos-entrada/') and key.lower().endswith('.pdf'):
                logger.info(f"Processing PDF: {key}")
                
                # Process the PDF
                result = processor.process_uploaded_pdf(key)
                results.append(result)
                
                logger.info(f"Processing result: {result}")
            else:
                logger.info(f"Skipping non-PDF or wrong folder: {key}")
        
        # Return success response
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Successfully processed {len(results)} PDF(s)',
                'results': results
            })
        }
        
    except Exception as e:
        logger.error(f"Lambda function error: {str(e)}")
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'message': 'Failed to process PDF upload'
            })
        }