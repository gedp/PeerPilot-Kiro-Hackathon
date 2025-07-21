#!/bin/bash

# PeerPilot Serverless Deployment Script
# This script deploys the automated PDF processing pipeline to AWS Lambda

set -e  # Exit on any error

echo "🚀 PeerPilot Serverless Deployment"
echo "=================================="

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found!"
    echo "   Please create .env file with your AWS credentials"
    echo "   Copy from .env.example and update with your values"
    exit 1
fi

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Check required environment variables
if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
    echo "❌ Error: AWS credentials not found in .env file"
    echo "   Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY"
    exit 1
fi

echo "✅ Environment variables loaded"
echo "   Bucket: $S3_BUCKET_NAME"
echo "   Region: $AWS_DEFAULT_REGION"

# Check if serverless framework is installed
if ! command -v serverless &> /dev/null; then
    echo "📦 Installing Serverless Framework..."
   sudo npm install -g serverless
fi

# Check if serverless plugins are installed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing Serverless plugins..."
    npm init -y
    npm install serverless-python-requirements
fi

# Create S3 bucket if it doesn't exist
echo "📦 Creating S3 bucket if needed..."
python3 -c "
from src.s3_client import S3Client
s3 = S3Client()
if s3.create_bucket_if_not_exists():
    print('✅ S3 bucket ready')
else:
    print('❌ Failed to create S3 bucket')
    exit(1)
"

# Test local processing first
echo "🧪 Testing local processing..."
python3 -c "
import sys
from src.document_processor import DocumentProcessor
from src.s3_client import S3Client

try:
    processor = DocumentProcessor()
    s3_client = S3Client()
    print('✅ Local components initialized successfully')
except Exception as e:
    print(f'❌ Local test failed: {e}')
    sys.exit(1)
"

# Deploy to AWS Lambda
echo "🚀 Deploying to AWS Lambda..."
serverless deploy --verbose

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Deployment Successful!"
    echo "========================"
    echo ""
    echo "Your automated PDF processing pipeline is now active!"
    echo ""
    echo "📋 What happens next:"
    echo "   1. Upload PDF files to: s3://$S3_BUCKET_NAME/articulos-entrada/"
    echo "   2. Lambda function will automatically trigger"
    echo "   3. Textract will extract text from PDFs"
    echo "   4. Results saved to: s3://$S3_BUCKET_NAME/processed-articles/"
    echo ""
    echo "🧪 Test the pipeline:"
    echo "   python3 monitor_processing.py"
    echo ""
    echo "📊 Monitor Lambda logs:"
    echo "   serverless logs -f processDocument -t"
    echo ""
    echo "🗑️ To remove deployment:"
    echo "   serverless remove"
else
    echo "❌ Deployment failed!"
    echo "   Check the error messages above"
    echo "   Common issues:"
    echo "   - AWS credentials not properly configured"
    echo "   - Insufficient IAM permissions"
    echo "   - S3 bucket name conflicts"
    exit 1
fi
