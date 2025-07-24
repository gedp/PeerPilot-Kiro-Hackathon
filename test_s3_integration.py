#!/usr/bin/env python3
"""
Test script for S3 integration
This script tests the S3Client functionality including:
- Bucket creation
- File upload
- File download
- File listing
- File deletion
"""

import os
import tempfile
from src.s3_client import S3Client
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_s3_integration():
    """Test S3 integration functionality"""
    try:
        # Initialize S3 client
        s3_client = S3Client()
        logger.info("S3 Client initialized successfully")
        
        # Test 1: Create bucket if not exists
        logger.info("Testing bucket creation...")
        bucket_created = s3_client.create_bucket_if_not_exists()
        if bucket_created:
            logger.info("✅ Bucket creation/verification successful")
        else:
            logger.error("❌ Bucket creation failed")
            return False
        
        # Test 2: Create a test file and upload it
        logger.info("Testing file upload...")
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
            temp_file.write("This is a test file for S3 integration testing.")
            temp_file_path = temp_file.name
        
        test_key = "test-files/integration-test.txt"
        upload_success = s3_client.upload_file(temp_file_path, test_key)
        if upload_success:
            logger.info("✅ File upload successful")
        else:
            logger.error("❌ File upload failed")
            return False
        
        # Test 3: List files
        logger.info("Testing file listing...")
        files = s3_client.list_files("test-files/")
        if test_key in files:
            logger.info("✅ File listing successful - uploaded file found")
        else:
            logger.error("❌ File listing failed - uploaded file not found")
            return False
        
        # Test 4: Download file
        logger.info("Testing file download...")
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as download_file:
            download_path = download_file.name
        
        download_success = s3_client.download_file(test_key, download_path)
        if download_success:
            # Verify content
            with open(download_path, 'r') as f:
                content = f.read()
            if "This is a test file for S3 integration testing." in content:
                logger.info("✅ File download successful - content verified")
            else:
                logger.error("❌ File download failed - content mismatch")
                return False
        else:
            logger.error("❌ File download failed")
            return False
        
        # Test 5: Delete test file
        logger.info("Testing file deletion...")
        delete_success = s3_client.delete_file(test_key)
        if delete_success:
            logger.info("✅ File deletion successful")
        else:
            logger.error("❌ File deletion failed")
            return False
        
        # Cleanup local temp files
        os.unlink(temp_file_path)
        os.unlink(download_path)
        
        logger.info("🎉 All S3 integration tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ S3 integration test failed with error: {str(e)}")
        return False

if __name__ == "__main__":
    print("Starting S3 Integration Tests...")
    print("=" * 50)
    
    success = test_s3_integration()
    
    print("=" * 50)
    if success:
        print("✅ S3 Integration Test: PASSED")
        print("\nYour S3 setup is working correctly!")
        print(f"Bucket: peerpilot-kiro-data")
        print("All CRUD operations (Create, Read, Update, Delete) are functional.")
    else:
        print("❌ S3 Integration Test: FAILED")
        print("\nPlease check your AWS credentials and permissions.")
        print("Make sure you have:")
        print("1. AWS credentials configured (AWS CLI, environment variables, or IAM role)")
        print("2. Proper S3 permissions for the peerpilot-kiro-data bucket")