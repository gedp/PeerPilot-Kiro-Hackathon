import boto3
import json
import time
from botocore.exceptions import ClientError
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

class TextractClient:
    def __init__(self):
        self.textract = boto3.client('textract')
        self.s3 = boto3.client('s3')
    
    def extract_text_from_pdf(self, bucket_name, pdf_key):
        """
        Extract text from PDF using Amazon Textract
        Returns the extracted text as a string
        """
        try:
            # Start document text detection job
            response = self.textract.start_document_text_detection(
                DocumentLocation={
                    'S3Object': {
                        'Bucket': bucket_name,
                        'Name': pdf_key
                    }
                }
            )
            
            job_id = response['JobId']
            logger.info(f"Started Textract job {job_id} for {pdf_key}")
            
            # Wait for job completion
            while True:
                response = self.textract.get_document_text_detection(JobId=job_id)
                status = response['JobStatus']
                
                if status == 'SUCCEEDED':
                    break
                elif status == 'FAILED':
                    raise Exception(f"Textract job failed: {response.get('StatusMessage', 'Unknown error')}")
                else:
                    logger.info(f"Job {job_id} status: {status}, waiting...")
                    time.sleep(5)
            
            # Extract text from all pages
            extracted_text = []
            next_token = None
            
            while True:
                if next_token:
                    response = self.textract.get_document_text_detection(
                        JobId=job_id,
                        NextToken=next_token
                    )
                else:
                    response = self.textract.get_document_text_detection(JobId=job_id)
                
                # Extract text blocks
                for block in response['Blocks']:
                    if block['BlockType'] == 'LINE':
                        extracted_text.append(block['Text'])
                
                next_token = response.get('NextToken')
                if not next_token:
                    break
            
            full_text = '\n'.join(extracted_text)
            logger.info(f"Successfully extracted {len(full_text)} characters from {pdf_key}")
            
            return full_text
            
        except ClientError as e:
            logger.error(f"AWS error extracting text from {pdf_key}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error extracting text from {pdf_key}: {e}")
            raise
    
    def extract_text_sync(self, bucket_name, pdf_key):
        """
        Extract text from PDF using synchronous Textract (for smaller documents)
        """
        try:
            # Get the PDF from S3
            response = self.s3.get_object(Bucket=bucket_name, Key=pdf_key)
            pdf_content = response['Body'].read()
            
            # Use synchronous text detection for smaller files
            response = self.textract.detect_document_text(
                Document={'Bytes': pdf_content}
            )
            
            # Extract text
            extracted_text = []
            for block in response['Blocks']:
                if block['BlockType'] == 'LINE':
                    extracted_text.append(block['Text'])
            
            full_text = '\n'.join(extracted_text)
            logger.info(f"Successfully extracted {len(full_text)} characters from {pdf_key} (sync)")
            
            return full_text
            
        except ClientError as e:
            logger.error(f"AWS error in sync extraction from {pdf_key}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error in sync extraction from {pdf_key}: {e}")
            raise
    
    def create_extraction_metadata(self, pdf_key, text_length, extraction_method):
        """Create metadata about the extraction process"""
        return {
            "original_file": pdf_key,
            "extraction_timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "text_length": text_length,
            "extraction_method": extraction_method,
            "status": "completed"
        }