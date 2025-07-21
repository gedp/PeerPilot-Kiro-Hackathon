# S3 Integration Design Document

## Overview

The S3 integration will be implemented as a Python module that provides a clean, high-level interface for interacting with Amazon S3. The design follows the boto3 library patterns while abstracting away complexity and providing robust error handling. The module will handle AWS credential management, bucket operations, and file transfers with comprehensive logging and error reporting.

## Architecture

The S3 integration follows a layered architecture:

```
AI Agent Application
        ↓
S3Client (High-level interface)
        ↓
S3Service (Business logic layer)
        ↓
boto3 (AWS SDK)
        ↓
Amazon S3
```

### Key Components:
- **S3Client**: Public interface for the AI agent
- **S3Service**: Internal service handling AWS operations
- **Configuration**: AWS credential and bucket management
- **Error Handling**: Custom exceptions and error recovery

## Components and Interfaces

### S3Client Class
```python
class S3Client:
    def __init__(self, bucket_name: str = "peerpilot-kiro-data")
    def upload_file(self, local_path: str, s3_key: str = None) -> str
    def download_file(self, s3_key: str, local_path: str) -> str
    def list_files(self, prefix: str = "") -> List[Dict[str, Any]]
    def file_exists(self, s3_key: str) -> bool
    def delete_file(self, s3_key: str) -> bool
```

### S3Service Class (Internal)
```python
class S3Service:
    def __init__(self, bucket_name: str)
    def _ensure_bucket_exists(self) -> None
    def _get_s3_client(self) -> boto3.client
    def _validate_credentials(self) -> bool
```

### Configuration Management
- Environment variables: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`
- AWS credentials file: `~/.aws/credentials`
- IAM roles (for EC2/Lambda deployment)
- Default region: `us-east-1`

## Data Models

### File Metadata
```python
@dataclass
class S3FileInfo:
    key: str
    size: int
    last_modified: datetime
    etag: str
    storage_class: str
```

### Configuration
```python
@dataclass
class S3Config:
    bucket_name: str
    region: str
    access_key_id: Optional[str]
    secret_access_key: Optional[str]
```

## Error Handling

### Custom Exceptions
```python
class S3IntegrationError(Exception): pass
class S3CredentialsError(S3IntegrationError): pass
class S3BucketError(S3IntegrationError): pass
class S3FileNotFoundError(S3IntegrationError): pass
class S3UploadError(S3IntegrationError): pass
class S3DownloadError(S3IntegrationError): pass
```

### Error Recovery Strategies
- Retry logic for transient network errors (exponential backoff)
- Clear error messages with actionable suggestions
- Graceful degradation when possible
- Comprehensive logging for debugging

## Security Considerations

### Credential Management
- Never hardcode credentials in source code
- Support multiple credential sources (env vars, files, IAM roles)
- Validate credentials before performing operations
- Use least-privilege IAM policies

### Bucket Security
- Enable versioning for data protection
- Configure appropriate bucket policies
- Use server-side encryption (AES-256)
- Enable access logging for audit trails

### Recommended IAM Policy
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::peerpilot-kiro-data",
                "arn:aws:s3:::peerpilot-kiro-data/*"
            ]
        }
    ]
}
```

## Testing Strategy

### Unit Tests
- Mock boto3 client for isolated testing
- Test all public methods of S3Client
- Test error conditions and exception handling
- Test credential validation logic

### Integration Tests
- Test against real S3 bucket (separate test bucket)
- Test file upload/download roundtrip
- Test bucket creation and configuration
- Test with different credential sources

### Test Structure
```
tests/
├── unit/
│   ├── test_s3_client.py
│   ├── test_s3_service.py
│   └── test_config.py
├── integration/
│   ├── test_s3_operations.py
│   └── test_bucket_management.py
└── fixtures/
    ├── sample_files/
    └── mock_responses.py
```

## Dependencies

### Required Packages
- `boto3>=1.26.0` - AWS SDK for Python
- `botocore>=1.29.0` - Low-level AWS service access
- `python-dotenv>=0.19.0` - Environment variable management
- `typing-extensions>=4.0.0` - Type hints support

### Development Dependencies
- `pytest>=7.0.0` - Testing framework
- `pytest-mock>=3.6.0` - Mocking utilities
- `moto>=4.0.0` - AWS service mocking for tests
- `black>=22.0.0` - Code formatting
- `mypy>=0.950` - Type checking

## File Structure

```
s3_integration/
├── __init__.py
├── client.py          # S3Client class
├── service.py         # S3Service class
├── config.py          # Configuration management
├── exceptions.py      # Custom exceptions
└── utils.py          # Utility functions

tests/
├── unit/
├── integration/
└── fixtures/

requirements.txt
setup.py
README.md
```

## Usage Examples

### Basic Usage
```python
from s3_integration import S3Client

# Initialize client
s3_client = S3Client()

# Upload a file
s3_key = s3_client.upload_file("local_file.txt")
print(f"Uploaded to: {s3_key}")

# Download a file
local_path = s3_client.download_file("remote_file.txt", "downloaded_file.txt")
print(f"Downloaded to: {local_path}")

# List files
files = s3_client.list_files(prefix="data/")
for file_info in files:
    print(f"{file_info['key']} - {file_info['size']} bytes")
```

### Advanced Usage
```python
# Custom bucket and configuration
s3_client = S3Client(bucket_name="custom-bucket")

# Upload with custom key
s3_client.upload_file("report.pdf", s3_key="reports/2024/january.pdf")

# Check if file exists before download
if s3_client.file_exists("important_data.json"):
    s3_client.download_file("important_data.json", "local_data.json")
```