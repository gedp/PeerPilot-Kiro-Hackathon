#!/usr/bin/env python3
"""
S3 Usage Example
This script demonstrates how to use the S3Client for common operations
"""

from src.s3_client import S3Client
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Example usage of S3Client"""
    
    # Initialize S3 client (uses environment variables or defaults)
    s3_client = S3Client()
    
    # Create bucket if it doesn't exist
    print("Creating/verifying S3 bucket...")
    s3_client.create_bucket_if_not_exists()
    
    # Example 1: Upload a file
    print("\n1. Uploading a file...")
    # s3_client.upload_file("local_file.pdf", "documents/my-document.pdf")
    
    # Example 2: Download a file
    print("2. Downloading a file...")
    # s3_client.download_file("documents/my-document.pdf", "downloaded_file.pdf")
    
    # Example 3: List files in a folder
    print("3. Listing files...")
    files = s3_client.list_files("input-articles/")
    print(f"Found {len(files)} files in input-articles/ folder:")
    for file in files[:5]:  # Show first 5 files
        print(f"  - {file}")
    
    # Example 4: List all files
    print("\n4. Listing all files in bucket...")
    all_files = s3_client.list_files()
    print(f"Total files in bucket: {len(all_files)}")
    
    # Example 5: Delete a file
    print("5. Deleting a file...")
    # s3_client.delete_file("documents/old-document.pdf")
    
    print("\n✅ S3 operations completed!")
    print(f"Bucket: {s3_client.bucket_name}")
    print(f"Region: {s3_client.region}")

if __name__ == "__main__":
    main()