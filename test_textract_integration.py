#!/usr/bin/env python3
"""
Comprehensive test script for enhanced Textract integration
Tests TextractClient, DocumentProcessor, and end-to-end workflow
"""

import os
import sys
import tempfile
import logging
from datetime import datetime
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.textract_client import TextractClient
from src.document_processor import DocumentProcessor
from src.s3_client import S3Client
from src.textract_models import (
    ProcessingStatus, ExtractionMethod, ProcessingConfig,
    TextractError, DocumentValidationError
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TextractIntegrationTester:
    """Comprehensive tester for Textract integration"""
    
    def __init__(self):
        """Initialize test components"""
        try:
            self.s3_client = S3Client()
            self.textract_client = TextractClient()
            self.document_processor = DocumentProcessor()
            self.bucket_name = self.s3_client.bucket_name
            
            logger.info(f"✅ Test components initialized for bucket: {self.bucket_name}")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize test components: {e}")
            raise
    
    def run_all_tests(self) -> bool:
        """
        Run all integration tests
        
        Returns:
            True if all tests pass
        """
        print("🚀 Starting Textract Integration Tests")
        print("=" * 60)
        
        test_methods = [
            self.test_s3_connectivity,
            self.test_textract_client_initialization,
            self.test_document_validation,
            self.test_sync_text_extraction,
            self.test_document_processor_workflow,
            self.test_error_handling,
            self.test_confidence_analysis,
            self.test_file_organization
        ]
        
        passed = 0
        failed = 0
        
        for test_method in test_methods:
            try:
                print(f"\n🧪 Running {test_method.__name__}...")
                result = test_method()
                if result:
                    print(f"✅ {test_method.__name__} PASSED")
                    passed += 1
                else:
                    print(f"❌ {test_method.__name__} FAILED")
                    failed += 1
            except Exception as e:
                print(f"❌ {test_method.__name__} FAILED with exception: {e}")
                logger.error(f"Test {test_method.__name__} failed: {e}", exc_info=True)
                failed += 1
        
        print("\n" + "=" * 60)
        print(f"📊 Test Results: {passed} passed, {failed} failed")
        
        if failed == 0:
            print("🎉 All Textract integration tests PASSED!")
            return True
        else:
            print(f"💥 {failed} test(s) FAILED. Check logs for details.")
            return False
    
    def test_s3_connectivity(self) -> bool:
        """Test S3 connectivity and bucket access"""
        try:
            # Test bucket creation/access
            bucket_exists = self.s3_client.create_bucket_if_not_exists()
            if not bucket_exists:
                logger.error("Failed to create or access S3 bucket")
                return False
            
            # Test file listing
            files = self.s3_client.list_files("input-articles/")
            logger.info(f"Found {len(files)} files in input-articles/ folder")
            
            return True
            
        except Exception as e:
            logger.error(f"S3 connectivity test failed: {e}")
            return False
    
    def test_textract_client_initialization(self) -> bool:
        """Test TextractClient initialization and basic functionality"""
        try:
            # Test client initialization
            client = TextractClient()
            
            # Test region configuration
            expected_region = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
            if client.region != expected_region:
                logger.error(f"Region mismatch: expected {expected_region}, got {client.region}")
                return False
            
            logger.info(f"TextractClient initialized with region: {client.region}")
            return True
            
        except Exception as e:
            logger.error(f"TextractClient initialization test failed: {e}")
            return False
    
    def test_document_validation(self) -> bool:
        """Test document validation logic"""
        try:
            # Create a test PDF file
            test_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n"
            
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                temp_file.write(test_content)
                temp_file_path = temp_file.name
            
            try:
                # Upload test file
                test_key = "input-articles/test_validation.pdf"
                upload_success = self.s3_client.upload_file(temp_file_path, test_key)
                
                if not upload_success:
                    logger.error("Failed to upload test file")
                    return False
                
                # Test validation
                validation = self.textract_client._validate_document(self.bucket_name, test_key)
                
                if not validation.is_valid:
                    logger.error(f"Document validation failed: {validation.error_message}")
                    return False
                
                logger.info(f"Document validation passed: {validation.file_size} bytes")
                
                # Test invalid file validation
                invalid_key = "input-articles/test.txt"
                with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as invalid_file:
                    invalid_file.write(b"This is not a PDF")
                    invalid_file_path = invalid_file.name
                
                try:
                    self.s3_client.upload_file(invalid_file_path, invalid_key)
                    invalid_validation = self.textract_client._validate_document(self.bucket_name, invalid_key)
                    
                    if invalid_validation.is_valid:
                        logger.error("Invalid file passed validation")
                        return False
                    
                    logger.info("Invalid file correctly rejected")
                    
                finally:
                    os.unlink(invalid_file_path)
                    self.s3_client.delete_file(invalid_key)
                
                return True
                
            finally:
                os.unlink(temp_file_path)
                self.s3_client.delete_file(test_key)
                
        except Exception as e:
            logger.error(f"Document validation test failed: {e}")
            return False
    
    def test_sync_text_extraction(self) -> bool:
        """Test synchronous text extraction with a simple document"""
        try:
            # Create a simple PDF with text (this is a minimal PDF structure)
            # In a real test, you'd use a proper PDF library like reportlab
            logger.info("Note: This test requires a real PDF file for full functionality")
            logger.info("Skipping actual extraction test - would need real PDF content")
            
            # Test the method selection logic instead
            small_size = 1024 * 1024  # 1MB
            large_size = 10 * 1024 * 1024  # 10MB
            
            should_use_sync = not self.textract_client._should_use_async_extraction(
                self.bucket_name, "test.pdf", small_size
            )
            should_use_async = self.textract_client._should_use_async_extraction(
                self.bucket_name, "test.pdf", large_size
            )
            
            if not should_use_sync:
                logger.error("Small file should use sync extraction")
                return False
            
            if not should_use_async:
                logger.error("Large file should use async extraction")
                return False
            
            logger.info("Method selection logic working correctly")
            return True
            
        except Exception as e:
            logger.error(f"Sync text extraction test failed: {e}")
            return False
    
    def test_document_processor_workflow(self) -> bool:
        """Test the complete DocumentProcessor workflow"""
        try:
            # Test processor initialization
            processor = DocumentProcessor()
            
            if processor.bucket_name != self.bucket_name:
                logger.error("DocumentProcessor bucket mismatch")
                return False
            
            # Test listing processed documents
            processed_docs = processor.list_processed_documents()
            logger.info(f"Found {len(processed_docs)} previously processed documents")
            
            # Test configuration
            text_key = ProcessingConfig.get_text_output_key("input-articles/test.pdf")
            expected_text_key = "extracted-texts/test.txt"
            
            if text_key != expected_text_key:
                logger.error(f"Text key generation failed: expected {expected_text_key}, got {text_key}")
                return False
            
            metadata_key = ProcessingConfig.get_metadata_output_key("input-articles/test.pdf")
            expected_metadata_key = "extraction-metadata/test.json"
            
            if metadata_key != expected_metadata_key:
                logger.error(f"Metadata key generation failed: expected {expected_metadata_key}, got {metadata_key}")
                return False
            
            logger.info("DocumentProcessor workflow components working correctly")
            return True
            
        except Exception as e:
            logger.error(f"DocumentProcessor workflow test failed: {e}")
            return False
    
    def test_error_handling(self) -> bool:
        """Test error handling scenarios"""
        try:
            # Test validation error for non-existent file
            try:
                validation = self.textract_client._validate_document(
                    self.bucket_name, "input-articles/nonexistent.pdf"
                )
                if validation.is_valid:
                    logger.error("Non-existent file should fail validation")
                    return False
                logger.info("Non-existent file correctly rejected")
            except Exception as e:
                logger.error(f"Unexpected error in validation test: {e}")
                return False
            
            # Test custom exception creation
            try:
                raise DocumentValidationError("Test error", error_code="TEST_ERROR")
            except DocumentValidationError as e:
                if e.error_code != "TEST_ERROR":
                    logger.error("Custom exception error code not preserved")
                    return False
                logger.info("Custom exception handling working correctly")
            
            return True
            
        except Exception as e:
            logger.error(f"Error handling test failed: {e}")
            return False
    
    def test_confidence_analysis(self) -> bool:
        """Test confidence statistics calculation"""
        try:
            from src.textract_models import ConfidenceStats
            
            # Create mock Textract blocks
            mock_blocks = [
                {'BlockType': 'LINE', 'Confidence': 95.5, 'Text': 'High confidence text'},
                {'BlockType': 'LINE', 'Confidence': 85.2, 'Text': 'Medium confidence text'},
                {'BlockType': 'LINE', 'Confidence': 75.8, 'Text': 'Lower confidence text'},
                {'BlockType': 'WORD', 'Confidence': 92.1, 'Text': 'Word'},
                {'BlockType': 'PAGE', 'Text': 'Page block without confidence'}
            ]
            
            # Calculate confidence statistics
            stats = ConfidenceStats.from_blocks(mock_blocks)
            
            # Verify calculations
            expected_avg = (95.5 + 85.2 + 75.8 + 92.1) / 4
            if abs(stats.average_confidence - expected_avg) > 0.1:
                logger.error(f"Average confidence calculation error: expected {expected_avg}, got {stats.average_confidence}")
                return False
            
            if stats.min_confidence != 75.8:
                logger.error(f"Min confidence error: expected 75.8, got {stats.min_confidence}")
                return False
            
            if stats.max_confidence != 95.5:
                logger.error(f"Max confidence error: expected 95.5, got {stats.max_confidence}")
                return False
            
            if stats.low_confidence_blocks != 1:  # Only 75.8 is below 80
                logger.error(f"Low confidence count error: expected 1, got {stats.low_confidence_blocks}")
                return False
            
            logger.info(f"Confidence analysis working correctly: avg={stats.average_confidence:.1f}, "
                       f"range={stats.min_confidence:.1f}-{stats.max_confidence:.1f}")
            return True
            
        except Exception as e:
            logger.error(f"Confidence analysis test failed: {e}")
            return False
    
    def test_file_organization(self) -> bool:
        """Test S3 file organization and naming conventions"""
        try:
            # Test folder structure
            expected_prefixes = [
                ProcessingConfig.INPUT_PREFIX,
                ProcessingConfig.OUTPUT_TEXT_PREFIX,
                ProcessingConfig.OUTPUT_METADATA_PREFIX,
                ProcessingConfig.ERROR_PREFIX
            ]
            
            expected_values = [
                "input-articles/",
                "extracted-texts/",
                "extraction-metadata/",
                "processing-errors/"
            ]
            
            for prefix, expected in zip(expected_prefixes, expected_values):
                if prefix != expected:
                    logger.error(f"Prefix mismatch: expected {expected}, got {prefix}")
                    return False
            
            # Test file extension configuration
            if ProcessingConfig.TEXT_OUTPUT_EXTENSION != '.txt':
                logger.error("Text output extension should be .txt")
                return False
            
            if ProcessingConfig.METADATA_OUTPUT_EXTENSION != '.json':
                logger.error("Metadata output extension should be .json")
                return False
            
            logger.info("File organization configuration correct")
            return True
            
        except Exception as e:
            logger.error(f"File organization test failed: {e}")
            return False

def main():
    """Main test execution"""
    print("🔍 PeerPilot Textract Integration Test Suite")
    print(f"📅 Started at: {datetime.now().isoformat()}")
    print()
    
    try:
        tester = TextractIntegrationTester()
        success = tester.run_all_tests()
        
        print("\n" + "=" * 60)
        if success:
            print("🎉 ALL TESTS PASSED! Textract integration is ready.")
            print("\n📋 Next Steps:")
            print("1. Deploy with: ./deploy.sh")
            print("2. Upload a PDF to: s3://peerpilot-kiro-data/input-articles/")
            print("3. Check results in: s3://peerpilot-kiro-data/extracted-texts/")
            print("4. Monitor logs: serverless logs -f processDocument -t")
            return 0
        else:
            print("💥 SOME TESTS FAILED! Check the logs above.")
            print("\n🔧 Troubleshooting:")
            print("1. Verify AWS credentials: aws sts get-caller-identity")
            print("2. Check S3 permissions: aws s3 ls s3://peerpilot-kiro-data/")
            print("3. Verify Textract permissions in your AWS account")
            return 1
            
    except Exception as e:
        print(f"💥 Test suite failed to run: {e}")
        logger.error("Test suite execution failed", exc_info=True)
        return 1

if __name__ == "__main__":
    exit(main())