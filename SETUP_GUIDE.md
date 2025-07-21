# PeerPilot Automated Article Processing Setup Guide

## 🎯 Overview

This guide will help you set up the complete automated PDF processing pipeline for PeerPilot. The system automatically:

1. **Monitors** the `articulos-entrada/` folder in your S3 bucket
2. **Extracts text** from uploaded PDFs using Amazon Textract
3. **Saves results** to `processed-articles/` folder with metadata

## 🚀 Quick Start

### 1. Prerequisites

- AWS Account with appropriate permissions
- Python 3.9+ installed
- Node.js and npm (for Serverless Framework)

### 2. AWS Permissions Required

Your AWS user needs these permissions:
- `AmazonS3FullAccess` (or custom S3 policy for your bucket)
- `AmazonTextractFullAccess`
- `AWSLambdaFullAccess`
- `CloudFormationFullAccess`
- `IAMFullAccess` (for creating Lambda execution roles)

### 3. Environment Setup

```bash
# 1. Clone and navigate to project
cd PeerPilot-Kiro-Hackathon

# 2. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Update .env file with your AWS credentials
cp .env.example .env
# Edit .env with your actual AWS credentials
```

### 4. Configure AWS Credentials

Edit your `.env` file:
```bash
AWS_ACCESS_KEY_ID=your_actual_access_key
AWS_SECRET_ACCESS_KEY=your_actual_secret_key
AWS_DEFAULT_REGION=us-east-1
S3_BUCKET_NAME=peerpilot-kiro-data
```

### 5. Test Local Setup

```bash
# Test S3 connection and create bucket
python3 test_s3_setup.py

# Test the processing pipeline locally
python3 monitor_processing.py
```

### 6. Deploy Serverless Infrastructure

```bash
# One-command deployment
./deploy.sh
```

## 📁 S3 Bucket Structure

After setup, your bucket will have this structure:

```
peerpilot-kiro-data/
├── articulos-entrada/          # 📤 Upload PDFs here
│   ├── research_paper_1.pdf
│   └── article_draft_2.pdf
│
├── processed-articles/         # 📥 Extracted text appears here
│   ├── research_paper_1.txt
│   ├── research_paper_1_metadata.json
│   ├── article_draft_2.txt
│   └── article_draft_2_metadata.json
│
├── normas-revistas/           # 📋 Journal guidelines (future)
└── revisores-basico/          # 👥 Reviewer profiles (future)
```

## 🔄 How It Works

### Automatic Processing Flow

1. **Upload Trigger**: PDF uploaded to `articulos-entrada/`
2. **Lambda Activation**: S3 event triggers AWS Lambda function
3. **Text Extraction**: Amazon Textract processes the PDF
4. **Result Storage**: Text and metadata saved to `processed-articles/`

### File Naming Convention

- Input: `articulos-entrada/my_paper.pdf`
- Output: `processed-articles/my_paper.txt`
- Metadata: `processed-articles/my_paper_metadata.json`

## 🧪 Testing the Pipeline

### Method 1: Using Monitor Script
```bash
python3 monitor_processing.py
```
This script will:
- Upload a test PDF
- Monitor processing status
- Display results
- Clean up test files

### Method 2: Manual Upload
```bash
# Upload via AWS CLI
aws s3 cp your_paper.pdf s3://peerpilot-kiro-data/articulos-entrada/

# Or use the AWS Console to upload to the articulos-entrada/ folder
```

### Method 3: Programmatic Upload
```python
from src.s3_client import S3Client

s3_client = S3Client()
s3_client.upload_file("local_paper.pdf", "articulos-entrada/paper.pdf")
```

## 📊 Monitoring and Debugging

### View Lambda Logs
```bash
# Real-time logs
serverless logs -f processDocument -t

# Recent logs
serverless logs -f processDocument
```

### Check Processing Status
```python
from src.document_processor import DocumentProcessor

processor = DocumentProcessor()
processed_files = processor.list_processed_articles()
print(processed_files)
```

### Download Processed Text
```python
from src.document_processor import DocumentProcessor

processor = DocumentProcessor()
text = processor.get_processed_text("my_paper")
print(text)
```

## 🔧 Configuration Options

### Lambda Function Settings
- **Timeout**: 5 minutes (configurable in `serverless.yml`)
- **Memory**: 512MB (increase for larger PDFs)
- **Runtime**: Python 3.9

### Textract Processing
- **Async Processing**: For multi-page documents
- **Sync Processing**: Fallback for smaller files
- **Error Handling**: Automatic retry with different methods

## 🚨 Troubleshooting

### Common Issues

**1. "AWS credentials not found"**
```bash
# Check .env file
cat .env

# Test AWS connection
aws sts get-caller-identity
```

**2. "Bucket already exists" error**
- Bucket names must be globally unique
- Change `S3_BUCKET_NAME` in `.env` to something unique

**3. "Permission denied" errors**
- Verify IAM permissions
- Check AWS credentials are correct

**4. Lambda timeout errors**
- Increase timeout in `serverless.yml`
- Consider splitting large PDFs

**5. Textract processing fails**
- Check PDF is not password-protected
- Verify PDF is readable (not scanned image)
- Check AWS region supports Textract

### Debug Commands
```bash
# Test S3 connection
python3 -c "from src.s3_client import S3Client; S3Client().list_files()"

# Test Textract connection
python3 -c "from src.textract_client import TextractClient; print('Textract client OK')"

# Check Lambda deployment
serverless info

# Remove deployment (if needed)
serverless remove
```

## 💰 Cost Considerations

### AWS Service Costs
- **S3 Storage**: ~$0.023/GB/month
- **Lambda**: First 1M requests free, then $0.20/1M requests
- **Textract**: $1.50/1000 pages for document text detection

### Cost Optimization Tips
- Use S3 lifecycle policies for old files
- Monitor Lambda execution time
- Consider batch processing for high volumes

## 🔒 Security Best Practices

1. **Never commit `.env` file** (already in `.gitignore`)
2. **Use IAM roles** in production instead of access keys
3. **Enable S3 bucket encryption**
4. **Set up CloudTrail** for audit logging
5. **Use least-privilege IAM policies**

## 📈 Scaling Considerations

### For High Volume Processing
- Increase Lambda memory and timeout
- Use SQS for queue management
- Consider Step Functions for complex workflows
- Implement batch processing

### Monitoring at Scale
- Set up CloudWatch alarms
- Use X-Ray for tracing
- Implement custom metrics

## 🎉 Success Indicators

You'll know everything is working when:
- ✅ `test_s3_setup.py` passes all tests
- ✅ `monitor_processing.py` successfully processes test PDF
- ✅ Lambda logs show successful executions
- ✅ Processed text files appear in S3

## 🆘 Getting Help

If you encounter issues:
1. Check the troubleshooting section above
2. Review Lambda logs: `serverless logs -f processDocument`
3. Test components individually using the monitor script
4. Verify AWS permissions and credentials

Your automated article ingestion system is now ready to handle PDF uploads and extract text automatically! 🚀