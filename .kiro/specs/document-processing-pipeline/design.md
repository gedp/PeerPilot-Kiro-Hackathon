# PeerPilot Document Processing Pipeline - System Design

## Overview

The PeerPilot document processing pipeline is a comprehensive serverless system that automates the ingestion, text extraction, and analysis of academic papers. The system uses AWS services to provide scalable, reliable, and cost-effective document processing with intelligent method selection and robust error handling.

## Architecture

The system follows an event-driven, serverless architecture:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   S3 Upload     │───▶│  Lambda Trigger  │───▶│  Text Extraction│
│ input-articles/ │    │  (S3 Event)      │    │   (Textract)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
┌─────────────────┐    ┌──────────────────┐             │
│   S3 Storage    │◀───│  Result Storage  │◀────────────┘
│extracted-texts/ │    │   & Metadata     │
└─────────────────┘    └──────────────────┘
```

### Key Components:
- **S3Client**: Secure file storage and retrieval operations
- **TextractClient**: Intelligent text extraction with method selection
- **DocumentProcessor**: End-to-end workflow orchestration
- **Lambda Function**: Event-driven processing trigger
- **Data Models**: Structured result and metadata management

## Components and Interfaces

### TextractClient Class
```python
class TextractClient:
    def __init__(self, region_name: str = None)
    def extract_text_from_document(self, bucket_name: str, document_key: str) -> TextExtractionResult
    def _should_use_async_extraction(self, bucket_name: str, document_key: str, file_size: int) -> bool
    def _extract_text_async(self, bucket_name: str, document_key: str) -> Dict[str, Any]
    def _extract_text_sync(self, bucket_name: str, document_key: str) -> Dict[str, Any]
    def _wait_for_job_completion(self, job_id: str, max_wait_time: int = 300) -> Dict[str, Any]
    def _extract_text_from_blocks(self, blocks: List[Dict[str, Any]]) -> str
```

### DocumentProcessor Class
```python
class DocumentProcessor:
    def __init__(self, bucket_name: str = None)
    def process_uploaded_pdf(self, pdf_key: str) -> ProcessingResult
    def _extract_text_with_retry(self, pdf_key: str) -> TextExtractionResult
    def _save_extraction_results(self, pdf_key: str, result: TextExtractionResult) -> tuple[str, str]
    def _create_error_result(self, pdf_key: str, status: ProcessingStatus, error_message: str, start_time: datetime) -> ProcessingResult
    def list_processed_documents(self) -> List[ProcessedDocument]
    def get_extraction_result(self, document_name: str) -> Optional[TextExtractionResult]
    def get_processed_text(self, document_name: str) -> Optional[str]
```

### S3Client Class
```python
class S3Client:
    def __init__(self, bucket_name: str = None, region: str = None)
    def create_bucket_if_not_exists(self) -> bool
    def upload_file(self, local_file_path: str, s3_key: str = None) -> bool
    def download_file(self, s3_key: str, local_file_path: str) -> bool
    def list_files(self, prefix: str = "") -> List[str]
    def delete_file(self, s3_key: str) -> bool
```

## Data Models

### TextExtractionResult
```python
@dataclass
class TextExtractionResult:
    text_content: str
    confidence_stats: ConfidenceStats
    extraction_method: ExtractionMethod
    processing_time: float
    page_count: int
    character_count: int
    word_count: int
    metadata: Dict[str, Any]
    extraction_timestamp: datetime
```

### ConfidenceStats
```python
@dataclass
class ConfidenceStats:
    average_confidence: float
    min_confidence: float
    max_confidence: float
    low_confidence_blocks: int
    total_blocks: int
    confidence_distribution: Dict[str, int]
```

### ProcessingResult
```python
@dataclass
class ProcessingResult:
    status: ProcessingStatus
    original_file: str
    text_file_key: Optional[str]
    metadata_file_key: Optional[str]
    extraction_result: Optional[TextExtractionResult]
    error_message: Optional[str]
    processing_timestamp: datetime
```

## Processing Flow

### 1. Document Upload Flow
1. PDF uploaded to `s3://peerpilot-kiro-data/input-articles/`
2. S3 ObjectCreated event triggers Lambda function
3. Lambda invokes DocumentProcessor.process_uploaded_pdf()
4. Document validation (size, format, accessibility)
5. TextractClient.extract_text_from_document() called

### 2. Extraction Method Selection
```python
def _should_use_async_extraction(self, bucket_name: str, document_key: str, file_size: int) -> bool:
    """
    Decision logic for extraction method:
    - File size >= 5MB: Use async
    - Multi-page PDF: Use async
    - Single page < 5MB: Use sync
    """
```

### 3. Text Extraction Flow
**Async Flow:**
1. StartDocumentTextDetection()
2. Poll GetDocumentTextDetection() until complete
3. Extract text from all result blocks
4. Calculate confidence statistics

**Sync Flow:**
1. Download document from S3
2. DetectDocumentText() with document bytes
3. Extract text from result blocks
4. Calculate confidence statistics

### 4. Result Storage Flow
1. Save extracted text to `s3://bucket/extracted-texts/{name}.txt`
2. Save metadata to `s3://bucket/extraction-metadata/{name}.json`
3. Update processing status
4. Log completion metrics

## Error Handling Strategy

### Custom Exceptions
```python
class TextractError(Exception): pass
class DocumentValidationError(TextractError): pass
class ExtractionTimeoutError(TextractError): pass
class UnsupportedDocumentError(TextractError): pass
class TextractServiceError(TextractError): pass
class ExtractionQualityError(TextractError): pass
```

### Error Recovery
- **Retry Logic**: 3 attempts with exponential backoff for transient failures
- **Fallback Methods**: Automatic fallback between sync/async methods
- **Error Storage**: Detailed error information stored in `processing-errors/`
- **Graceful Degradation**: Continue processing other documents on individual failures

## Configuration Management

### Environment Variables
- `S3_BUCKET_NAME`: Target S3 bucket (default: peerpilot-kiro-data)
- `AWS_DEFAULT_REGION`: AWS region (default: us-east-1)
- `TEXTRACT_MAX_WAIT_TIME`: Maximum wait time for async jobs (default: 600s)
- `SYNC_EXTRACTION_SIZE_LIMIT`: Size limit for sync extraction (default: 5MB)
- `MIN_CONFIDENCE_THRESHOLD`: Minimum acceptable confidence (default: 80%)

### Processing Configuration
```python
class ProcessingConfig:
    SYNC_SIZE_LIMIT_MB = 5
    MAX_ASYNC_WAIT_TIME = 600
    MIN_CONFIDENCE_THRESHOLD = 80.0
    RETRY_ATTEMPTS = 3
    RETRY_DELAY = 5
    
    # S3 Prefixes
    INPUT_PREFIX = "input-articles/"
    OUTPUT_TEXT_PREFIX = "extracted-texts/"
    OUTPUT_METADATA_PREFIX = "extraction-metadata/"
    ERROR_PREFIX = "processing-errors/"
```

## Security Considerations

### IAM Permissions
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:GetObjectVersion",
                "s3:PutObject",
                "s3:PutObjectAcl",
                "s3:DeleteObject",
                "s3:ListBucket",
                "s3:GetBucketLocation",
                "s3:CreateBucket"
            ],
            "Resource": [
                "arn:aws:s3:::peerpilot-kiro-data",
                "arn:aws:s3:::peerpilot-kiro-data/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "textract:StartDocumentTextDetection",
                "textract:GetDocumentTextDetection",
                "textract:DetectDocumentText",
                "textract:AnalyzeDocument",
                "textract:StartDocumentAnalysis",
                "textract:GetDocumentAnalysis"
            ],
            "Resource": "*"
        }
    ]
}
```

### Data Protection
- Encryption at rest for S3 storage
- Secure transmission of document data
- No sensitive data in logs
- Public access blocked on S3 bucket

## Performance Optimization

### Intelligent Processing
- **Method Selection**: Automatic sync/async selection based on document characteristics
- **Concurrent Processing**: Lambda can handle multiple documents simultaneously
- **Resource Management**: Efficient memory usage for large documents
- **Cost Optimization**: Smart method selection reduces processing costs

### Monitoring and Metrics
- Processing time per document
- Success/failure rates
- Confidence score distributions
- Resource utilization metrics

## Scalability Design

### Horizontal Scaling
- Lambda auto-scales based on incoming events
- S3 provides unlimited storage capacity
- Textract handles concurrent requests automatically

### Resource Allocation
- Lambda: 15-minute timeout, 1GB memory for large documents
- Textract: Intelligent method selection for optimal performance
- S3: Organized folder structure for efficient access

## Testing Strategy

### Unit Tests
- TextractClient method selection logic
- DocumentProcessor workflow orchestration
- Data model serialization/deserialization
- Custom exception handling

### Integration Tests
- End-to-end document processing workflow
- S3 upload/download operations
- Textract extraction with real documents
- Error scenarios and recovery

### Performance Tests
- Large document processing (up to 500MB)
- Concurrent document processing
- Timeout and retry scenarios
- Resource utilization monitoring

## Deployment Architecture

### Serverless Configuration
```yaml
functions:
  processDocument:
    handler: lambda_function.lambda_handler
    timeout: 900  # 15 minutes
    memorySize: 1024  # 1GB
    environment:
      TEXTRACT_MAX_WAIT_TIME: 600
      SYNC_EXTRACTION_SIZE_LIMIT: 5
      MIN_CONFIDENCE_THRESHOLD: 80
    events:
      - s3:
          bucket: peerpilot-kiro-data
          existing: true
          event: s3:ObjectCreated:*
          rules:
            - prefix: input-articles/
            - suffix: .pdf
```

### File Organization
```
peerpilot-kiro-data/
├── input-articles/          # Incoming PDF documents
├── extracted-texts/         # Plain text extraction results
├── extraction-metadata/     # Processing metadata and statistics
└── processing-errors/       # Error information for failed processing
```

This design provides a robust, scalable, and maintainable document processing pipeline that can handle the demands of academic paper processing while providing comprehensive monitoring and error handling capabilities.