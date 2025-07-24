# PeerPilot Document Processing - System Design

## Architecture Overview

The PeerPilot document processing system follows a serverless, event-driven architecture using AWS services. The system is designed for scalability, reliability, and cost-effectiveness.

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

## Component Design

### 1. TextractClient Class

**Purpose**: Handles all Amazon Textract operations with intelligent method selection and robust error handling.

**Interface**:
```python
class TextractClient:
    def __init__(self, region_name: str = None)
    def extract_text_from_document(self, bucket_name: str, document_key: str) -> TextExtractionResult
    def _should_use_async_extraction(self, bucket_name: str, document_key: str) -> bool
    def _extract_text_async(self, bucket_name: str, document_key: str) -> TextExtractionResult
    def _extract_text_sync(self, bucket_name: str, document_key: str) -> TextExtractionResult
    def _wait_for_job_completion(self, job_id: str, max_wait_time: int = 300) -> dict
    def _extract_text_from_blocks(self, blocks: List[dict]) -> str
    def _calculate_confidence_stats(self, blocks: List[dict]) -> ConfidenceStats
```

**Key Features**:
- Intelligent selection between synchronous and asynchronous processing
- Comprehensive error handling with custom exceptions
- Confidence score analysis and reporting
- Efficient text extraction from Textract blocks
- Timeout handling for long-running jobs

### 2. DocumentProcessor Class

**Purpose**: Orchestrates the complete document processing workflow from S3 upload to result storage.

**Interface**:
```python
class DocumentProcessor:
    def __init__(self, bucket_name: str = None)
    def process_uploaded_pdf(self, pdf_key: str) -> ProcessingResult
    def _validate_document(self, pdf_key: str) -> ValidationResult
    def _extract_text_with_retry(self, pdf_key: str) -> TextExtractionResult
    def _save_extraction_results(self, pdf_key: str, result: TextExtractionResult) -> None
    def _generate_processing_metadata(self, pdf_key: str, result: TextExtractionResult) -> dict
    def list_processed_documents(self) -> List[ProcessedDocument]
    def get_extraction_result(self, document_name: str) -> Optional[TextExtractionResult]
```

**Key Features**:
- End-to-end processing orchestration
- Document validation and preprocessing
- Retry logic for failed extractions
- Structured result storage
- Processing history and status tracking

### 3. Data Models

#### TextExtractionResult
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
    metadata: dict
```

#### ConfidenceStats
```python
@dataclass
class ConfidenceStats:
    average_confidence: float
    min_confidence: float
    max_confidence: float
    low_confidence_blocks: int  # blocks with confidence < 80%
    total_blocks: int
```

#### ProcessingResult
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

#### Custom Exceptions
```python
class TextractError(Exception):
    """Base exception for Textract-related errors"""
    pass

class DocumentValidationError(TextractError):
    """Raised when document validation fails"""
    pass

class ExtractionTimeoutError(TextractError):
    """Raised when extraction job times out"""
    pass

class UnsupportedDocumentError(TextractError):
    """Raised when document format is not supported"""
    pass
```

### 4. Configuration Management

**Environment Variables**:
- `S3_BUCKET_NAME`: Target S3 bucket (default: peerpilot-kiro-data)
- `AWS_DEFAULT_REGION`: AWS region (default: us-east-1)
- `TEXTRACT_MAX_WAIT_TIME`: Maximum wait time for async jobs (default: 300s)
- `SYNC_EXTRACTION_SIZE_LIMIT`: Size limit for sync extraction (default: 5MB)
- `MIN_CONFIDENCE_THRESHOLD`: Minimum acceptable confidence (default: 80%)

**Constants**:
```python
class ProcessingConfig:
    SYNC_SIZE_LIMIT_MB = 5
    MAX_ASYNC_WAIT_TIME = 300
    MIN_CONFIDENCE_THRESHOLD = 80.0
    RETRY_ATTEMPTS = 3
    RETRY_DELAY = 5  # seconds
    
    # S3 Prefixes
    INPUT_PREFIX = "input-articles/"
    OUTPUT_TEXT_PREFIX = "extracted-texts/"
    OUTPUT_METADATA_PREFIX = "extraction-metadata/"
    ERROR_PREFIX = "processing-errors/"
```

## Processing Flow

### 1. Document Upload Flow
```
1. PDF uploaded to s3://peerpilot-kiro-data/input-articles/
2. S3 ObjectCreated event triggers Lambda function
3. Lambda invokes DocumentProcessor.process_uploaded_pdf()
4. Document validation (size, format, accessibility)
5. TextractClient.extract_text_from_document() called
```

### 2. Extraction Method Selection
```python
def _should_use_async_extraction(self, bucket_name: str, document_key: str) -> bool:
    """
    Decision logic for extraction method:
    - File size >= 5MB: Use async
    - Multi-page PDF: Use async
    - Single page < 5MB: Use sync
    """
```

### 3. Text Extraction Flow
```
Async Flow:
1. StartDocumentTextDetection()
2. Poll GetDocumentTextDetection() until complete
3. Extract text from all result blocks
4. Calculate confidence statistics

Sync Flow:
1. Download document from S3
2. DetectDocumentText() with document bytes
3. Extract text from result blocks
4. Calculate confidence statistics
```

### 4. Result Storage Flow
```
1. Save extracted text to s3://bucket/extracted-texts/{name}.txt
2. Save metadata to s3://bucket/extraction-metadata/{name}.json
3. Update processing status
4. Log completion metrics
```

## Error Handling Strategy

### 1. Error Categories
- **Validation Errors**: Document format, size, accessibility issues
- **Textract Errors**: Service limits, job failures, timeout errors
- **Storage Errors**: S3 upload/download failures
- **System Errors**: Memory, timeout, configuration issues

### 2. Error Recovery
```python
def _extract_text_with_retry(self, pdf_key: str) -> TextExtractionResult:
    """
    Retry strategy:
    1. Try async extraction
    2. If fails, try sync extraction
    3. If still fails, log error and raise exception
    """
```

### 3. Error Storage
- Error details stored in `s3://bucket/processing-errors/{name}_error.json`
- Structured error information for debugging
- Error metrics sent to CloudWatch

## Performance Considerations

### 1. Optimization Strategies
- **Method Selection**: Automatic sync/async selection based on document characteristics
- **Concurrent Processing**: Lambda can handle multiple documents simultaneously
- **Resource Management**: Efficient memory usage for large documents
- **Caching**: Avoid re-processing of identical documents

### 2. Monitoring and Metrics
- Processing time per document
- Success/failure rates
- Confidence score distributions
- Resource utilization metrics

## Security Design

### 1. Access Control
- IAM roles with minimal required permissions
- S3 bucket policies restricting access
- Lambda execution role with specific Textract permissions

### 2. Data Protection
- Encryption at rest for S3 storage
- Secure transmission of document data
- No sensitive data in logs

### 3. Audit Trail
- Complete processing history
- Error logging with context
- Performance metrics for compliance

## Scalability Design

### 1. Horizontal Scaling
- Lambda auto-scales based on incoming events
- S3 provides unlimited storage capacity
- Textract handles concurrent requests automatically

### 2. Performance Optimization
- Efficient document processing algorithms
- Minimal memory footprint
- Fast text extraction and storage

### 3. Cost Optimization
- Pay-per-use Lambda pricing model
- Efficient Textract API usage
- S3 storage class optimization

## Integration Points

### 1. S3Client Integration
- Consistent error handling patterns
- Shared configuration management
- Unified logging approach

### 2. Lambda Function Integration
- Event-driven processing model
- Proper error propagation
- Status reporting to calling function

### 3. Future Integrations
- CloudWatch monitoring
- SNS notifications for completion
- API Gateway for status queries