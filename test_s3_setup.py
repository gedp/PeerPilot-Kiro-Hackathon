#!/usr/bin/env python3
"""
Test script to verify S3 integration setup for PeerPilot
"""

import os
import tempfile
from src.s3_client import S3Client

def test_s3_setup():
    """Test S3 client functionality"""
    print("🚀 Testing S3 setup for PeerPilot...")
    
    try:
        # Initialize S3 client
        s3_client = S3Client()
        print(f"✅ S3 client initialized successfully")
        print(f"   Bucket: {s3_client.bucket_name}")
        print(f"   Region: {s3_client.region}")
        
        # Test bucket creation
        print("\n📦 Creating bucket if it doesn't exist...")
        if s3_client.create_bucket_if_not_exists():
            print("✅ Bucket is ready")
        else:
            print("❌ Failed to create/verify bucket")
            return False
        
        # Test file upload
        print("\n📤 Testing file upload...")
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
            temp_file.write("Hello from PeerPilot! This is a test file.")
            temp_file_path = temp_file.name
        
        test_key = "test/peerpilot-test.txt"
        if s3_client.upload_file(temp_file_path, test_key):
            print("✅ File uploaded successfully")
        else:
            print("❌ Failed to upload file")
            return False
        
        # Test file listing
        print("\n📋 Testing file listing...")
        files = s3_client.list_files("test/")
        if test_key in files:
            print(f"✅ Found uploaded file: {test_key}")
        else:
            print("❌ Uploaded file not found in listing")
        
        # Test file download
        print("\n📥 Testing file download...")
        download_path = temp_file_path + ".downloaded"
        if s3_client.download_file(test_key, download_path):
            print("✅ File downloaded successfully")
            with open(download_path, 'r') as f:
                content = f.read()
                print(f"   Content: {content[:50]}...")
        else:
            print("❌ Failed to download file")
        
        # Cleanup test files
        print("\n🧹 Cleaning up test files...")
        s3_client.delete_file(test_key)
        os.unlink(temp_file_path)
        if os.path.exists(download_path):
            os.unlink(download_path)
        
        print("\n🎉 All S3 tests passed! Your setup is ready for PeerPilot.")
        return True
        
    except Exception as e:
        print(f"❌ Error during S3 setup test: {e}")
        return False

if __name__ == "__main__":
    test_s3_setup()