#!/bin/bash

# Deployment script for PeerPilot Document Processor
# This script deploys the serverless application to AWS

set -e  # Exit on any error

echo "🚀 Starting deployment of PeerPilot Document Processor..."
echo "=================================================="

# Check if serverless is installed
if ! command -v serverless &> /dev/null; then
    echo "❌ Serverless Framework not found. Please install it first:"
    echo "   npm install -g serverless"
    exit 1
fi

# Check if AWS credentials are configured
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS credentials not configured. Please run 'aws configure' first."
    exit 1
fi

echo "✅ Prerequisites check passed"
echo ""

# Clean up any previous builds
echo "🧹 Cleaning up previous builds..."
rm -rf .serverless
echo "✅ Cleanup completed"
echo ""

# Deploy the service
echo "📦 Deploying serverless application..."
echo "   Runtime: Python 3.12"
echo "   Bucket: peerpilot-kiro-data"
echo "   Region: us-east-1"
echo ""

serverless deploy --verbose

echo ""
echo "🎉 Deployment completed successfully!"
echo "=================================================="
echo ""
echo "📋 Deployment Summary:"
echo "   Service: peerpilot-document-processor"
echo "   Runtime: python3.12"
echo "   S3 Bucket: peerpilot-kiro-data"
echo "   Region: us-east-1"
echo ""
echo "🔧 Next steps:"
echo "   1. Test S3 integration: python test_s3_integration.py"
echo "   2. Upload files to: s3://peerpilot-kiro-data/input-articles/"
echo "   3. Monitor logs: serverless logs -f processDocument -t"
echo ""
echo "✅ Ready to process documents!"