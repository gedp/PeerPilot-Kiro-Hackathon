import os
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from dotenv import load_dotenv
import logging
from typing import List, Optional, Dict, Any
import mimetypes
from pathlib import Path

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class S3Client:
    def __init__(self, bucket_name: Optional[str] = None, region: Optional[str] = None):
        """
        Initialize S3 client with bucket configuration
        
        Args:
            bucket_name: S3 bucket name (defaults to env var or 'peerpilot-kiro-data')
            region: AWS region (defaults to env var or 'us-east-1')
        """
        self.bucket_name = bucket_name or os.getenv('S3_BUCKET_NAME', 'peerpilot-kiro-data')
        self.region = region or os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        
        try:
            self.s3_client = boto3.client('s3', region_name=self.region)
            self.s3_resource = boto3.resource('s3', region_name=self.region)
            logger.info(f"S3 client initialized for bucket: {self.bucket_name} in region: {self.region}")
        except NoCredentialsError:
            raise Exception("AWS credentials not found. Please configure your credentials.")
        except Exception as e:
            raise Exception(f"Failed to initialize S3 client: {str(e)}")
    
    def create_bucket_if_not_exists(self) -> bool:
        """
        Create S3 bucket if it doesn't exist with proper security settings
        
        Returns:
            bool: True if bucket exists or was created successfully
        """
        try:
            # Check if bucket exists
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"Bucket {self.bucket_name} already exists")
            return True
        except ClientError as e:
            error_code = int(e.response['Error']['Code'])
            if error_code == 404:
                # Bucket doesn't exist, create it
                try:
                    if self.region == 'us-east-1':
                        self.s3_client.create_bucket(Bucket=self.bucket_name)
                    else:
                        self.s3_client.create_bucket(
                            Bucket=self.bucket_name,
                            CreateBucketConfiguration={'LocationConstraint': self.region}
                        )
                    
                    # Apply security settings
                    self._apply_bucket_security()
                    logger.info(f"Created bucket {self.bucket_name} with security settings")
                    return True
                except ClientError as create_error:
                    logger.error(f"Failed to create bucket: {create_error}")
                    return False
            else:
                logger.error(f"Error checking bucket: {e}")
                return False
    
    def _apply_bucket_security(self):
        """Apply security settings to the bucket"""
        try:
            # Block public access
            self.s3_client.put_public_access_block(
                Bucket=self.bucket_name,
                PublicAccessBlockConfiguration={
                    'BlockPublicAcls': True,
                    'IgnorePublicAcls': True,
                    'BlockPublicPolicy': True,
                    'RestrictPublicBuckets': True
                }
            )
            logger.info(f"Applied public access block to {self.bucket_name}")
        except ClientError as e:
            logger.warning(f"Failed to apply public access block: {e}")
    
    def upload_file(self, local_file_path, s3_key=None):
        """Upload a file to S3"""
        if s3_key is None:
            s3_key = os.path.basename(local_file_path)
        
        try:
            self.s3_client.upload_file(local_file_path, self.bucket_name, s3_key)
            logger.info(f"Uploaded {local_file_path} to s3://{self.bucket_name}/{s3_key}")
            return True
        except ClientError as e:
            logger.error(f"Failed to upload file: {e}")
            return False
    
    def download_file(self, s3_key, local_file_path):
        """Download a file from S3"""
        try:
            self.s3_client.download_file(self.bucket_name, s3_key, local_file_path)
            logger.info(f"Downloaded s3://{self.bucket_name}/{s3_key} to {local_file_path}")
            return True
        except ClientError as e:
            logger.error(f"Failed to download file: {e}")
            return False
    
    def list_files(self, prefix=""):
        """List files in the S3 bucket"""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            if 'Contents' in response:
                return [obj['Key'] for obj in response['Contents']]
            return []
        except ClientError as e:
            logger.error(f"Failed to list files: {e}")
            return []
    
    def delete_file(self, s3_key):
        """Delete a file from S3"""
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            logger.info(f"Deleted s3://{self.bucket_name}/{s3_key}")
            return True
        except ClientError as e:
            logger.error(f"Failed to delete file: {e}")
            return False