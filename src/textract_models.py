"""
Data models and types for Textract integration
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
import json


class ExtractionMethod(Enum):
    """Enumeration of text extraction methods"""
    SYNC = "synchronous"
    ASYNC = "asynchronous"
    FAILED = "failed"


class ProcessingStatus(Enum):
    """Enumeration of processing status values"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class ConfidenceStats:
    """Statistics about confidence scores from Textract"""
    average_confidence: float
    min_confidence: float
    max_confidence: float
    low_confidence_blocks: int  # blocks with confidence < 80%
    total_blocks: int
    confidence_distribution: Dict[str, int]  # ranges like "80-90": count
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)
    
    @classmethod
    def from_blocks(cls, blocks: List[Dict[str, Any]], threshold: float = 80.0) -> 'ConfidenceStats':
        """Calculate confidence statistics from Textract blocks"""
        if not blocks:
            return cls(0.0, 0.0, 0.0, 0, 0, {})
        
        confidences = []
        for block in blocks:
            if block.get('BlockType') in ['LINE', 'WORD'] and 'Confidence' in block:
                confidences.append(block['Confidence'])
        
        if not confidences:
            return cls(0.0, 0.0, 0.0, 0, 0, {})
        
        avg_confidence = sum(confidences) / len(confidences)
        min_confidence = min(confidences)
        max_confidence = max(confidences)
        low_confidence_count = sum(1 for c in confidences if c < threshold)
        
        # Calculate distribution
        distribution = {
            "0-50": sum(1 for c in confidences if 0 <= c < 50),
            "50-70": sum(1 for c in confidences if 50 <= c < 70),
            "70-80": sum(1 for c in confidences if 70 <= c < 80),
            "80-90": sum(1 for c in confidences if 80 <= c < 90),
            "90-95": sum(1 for c in confidences if 90 <= c < 95),
            "95-100": sum(1 for c in confidences if 95 <= c <= 100)
        }
        
        return cls(
            average_confidence=avg_confidence,
            min_confidence=min_confidence,
            max_confidence=max_confidence,
            low_confidence_blocks=low_confidence_count,
            total_blocks=len(confidences),
            confidence_distribution=distribution
        )


@dataclass
class TextExtractionResult:
    """Result of text extraction from a document"""
    text_content: str
    confidence_stats: ConfidenceStats
    extraction_method: ExtractionMethod
    processing_time: float
    page_count: int
    character_count: int
    word_count: int
    metadata: Dict[str, Any]
    extraction_timestamp: datetime
    
    def __post_init__(self):
        """Calculate derived fields after initialization"""
        if self.character_count == 0:
            self.character_count = len(self.text_content)
        if self.word_count == 0:
            self.word_count = len(self.text_content.split())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        result['confidence_stats'] = self.confidence_stats.to_dict()
        result['extraction_method'] = self.extraction_method.value
        result['extraction_timestamp'] = self.extraction_timestamp.isoformat()
        return result
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2)
    
    @property
    def is_high_quality(self) -> bool:
        """Check if extraction is high quality based on confidence"""
        return (self.confidence_stats.average_confidence >= 85.0 and 
                self.confidence_stats.low_confidence_blocks / max(self.confidence_stats.total_blocks, 1) < 0.1)


@dataclass
class ProcessingResult:
    """Result of complete document processing"""
    status: ProcessingStatus
    original_file: str
    text_file_key: Optional[str] = None
    metadata_file_key: Optional[str] = None
    extraction_result: Optional[TextExtractionResult] = None
    error_message: Optional[str] = None
    processing_timestamp: datetime = None
    
    def __post_init__(self):
        """Set default timestamp if not provided"""
        if self.processing_timestamp is None:
            self.processing_timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        result['status'] = self.status.value
        result['processing_timestamp'] = self.processing_timestamp.isoformat()
        if self.extraction_result:
            result['extraction_result'] = self.extraction_result.to_dict()
        return result
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2)


@dataclass
class ProcessedDocument:
    """Information about a processed document"""
    name: str
    original_key: str
    text_key: str
    metadata_key: str
    processing_date: datetime
    status: ProcessingStatus
    file_size: int
    processing_time: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        result['status'] = self.status.value
        result['processing_date'] = self.processing_date.isoformat()
        return result


@dataclass
class ValidationResult:
    """Result of document validation"""
    is_valid: bool
    file_size: int
    file_format: str
    error_message: Optional[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        """Initialize warnings list if None"""
        if self.warnings is None:
            self.warnings = []


# Custom Exceptions
class TextractError(Exception):
    """Base exception for Textract-related errors"""
    def __init__(self, message: str, error_code: str = None, original_error: Exception = None):
        super().__init__(message)
        self.error_code = error_code
        self.original_error = original_error
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging"""
        return {
            "error_type": self.__class__.__name__,
            "message": str(self),
            "error_code": self.error_code,
            "timestamp": self.timestamp.isoformat(),
            "original_error": str(self.original_error) if self.original_error else None
        }


class DocumentValidationError(TextractError):
    """Raised when document validation fails"""
    pass


class ExtractionTimeoutError(TextractError):
    """Raised when extraction job times out"""
    pass


class UnsupportedDocumentError(TextractError):
    """Raised when document format is not supported"""
    pass


class TextractServiceError(TextractError):
    """Raised when Textract service returns an error"""
    pass


class ExtractionQualityError(TextractError):
    """Raised when extraction quality is below acceptable threshold"""
    pass


# Configuration class
class ProcessingConfig:
    """Configuration constants for document processing"""
    
    # Size limits
    SYNC_SIZE_LIMIT_MB = 5
    MAX_DOCUMENT_SIZE_MB = 500
    
    # Timing
    MAX_ASYNC_WAIT_TIME = 300  # 5 minutes
    RETRY_ATTEMPTS = 3
    RETRY_DELAY = 5  # seconds
    POLL_INTERVAL = 5  # seconds for async job polling
    
    # Quality thresholds
    MIN_CONFIDENCE_THRESHOLD = 80.0
    MIN_AVERAGE_CONFIDENCE = 85.0
    MAX_LOW_CONFIDENCE_RATIO = 0.1
    
    # S3 Prefixes
    INPUT_PREFIX = "input-articles/"
    OUTPUT_TEXT_PREFIX = "extracted-texts/"
    OUTPUT_METADATA_PREFIX = "extraction-metadata/"
    ERROR_PREFIX = "processing-errors/"
    
    # File extensions
    SUPPORTED_EXTENSIONS = ['.pdf']
    TEXT_OUTPUT_EXTENSION = '.txt'
    METADATA_OUTPUT_EXTENSION = '.json'
    
    # Textract limits
    MAX_PAGES_SYNC = 1
    MAX_FILE_SIZE_SYNC_MB = 5
    
    @classmethod
    def get_text_output_key(cls, original_key: str) -> str:
        """Generate text output key from original key"""
        from pathlib import Path
        base_name = Path(original_key).stem
        return f"{cls.OUTPUT_TEXT_PREFIX}{base_name}{cls.TEXT_OUTPUT_EXTENSION}"
    
    @classmethod
    def get_metadata_output_key(cls, original_key: str) -> str:
        """Generate metadata output key from original key"""
        from pathlib import Path
        base_name = Path(original_key).stem
        return f"{cls.OUTPUT_METADATA_PREFIX}{base_name}{cls.METADATA_OUTPUT_EXTENSION}"
    
    @classmethod
    def get_error_output_key(cls, original_key: str) -> str:
        """Generate error output key from original key"""
        from pathlib import Path
        base_name = Path(original_key).stem
        return f"{cls.ERROR_PREFIX}{base_name}_error{cls.METADATA_OUTPUT_EXTENSION}"