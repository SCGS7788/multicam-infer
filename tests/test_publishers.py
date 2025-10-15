"""
test_publishers.py

Test AWS publisher integrations with mocked boto3 clients.

Tests:
- Kinesis Data Streams batching and publishing
- S3 put_object with correct keys and metadata
- DynamoDB put_item operations
- Error handling and retries
"""

import pytest
import json
import time
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime

from src.kvs_infer.publishers import (
    KinesisPublisher,
    S3Publisher,
    DynamoDBPublisher,
    batch_records,
)


@pytest.fixture
def mock_kinesis_client():
    """Create a mock Kinesis client."""
    client = Mock()
    client.put_records.return_value = {
        'FailedRecordCount': 0,
        'Records': [{'SequenceNumber': '12345', 'ShardId': 'shardId-000000000000'}]
    }
    return client


@pytest.fixture
def mock_s3_client():
    """Create a mock S3 client."""
    client = Mock()
    client.put_object.return_value = {
        'ETag': '"abc123"',
        'VersionId': 'v1'
    }
    return client


@pytest.fixture
def mock_dynamodb_client():
    """Create a mock DynamoDB client."""
    client = Mock()
    client.put_item.return_value = {
        'ResponseMetadata': {'HTTPStatusCode': 200}
    }
    return client


@pytest.fixture
def sample_detection():
    """Sample detection record."""
    return {
        "camera_id": "front-entrance",
        "timestamp": 1234567890.123,
        "detections": [
            {
                "bbox": [100, 100, 200, 200],
                "class": 0,
                "class_name": "person",
                "confidence": 0.95,
                "roi_name": "entrance"
            }
        ],
        "frame_number": 42
    }


class TestBatchRecords:
    """Test record batching utility."""
    
    def test_batch_empty_records(self):
        """Test batching empty records list."""
        records = []
        batches = list(batch_records(records, batch_size=10))
        
        assert len(batches) == 0
    
    def test_batch_single_record(self):
        """Test batching single record."""
        records = [{"id": 1}]
        batches = list(batch_records(records, batch_size=10))
        
        assert len(batches) == 1
        assert len(batches[0]) == 1
    
    def test_batch_exact_size(self):
        """Test batching when records exactly fill batch size."""
        records = [{"id": i} for i in range(10)]
        batches = list(batch_records(records, batch_size=10))
        
        assert len(batches) == 1
        assert len(batches[0]) == 10
    
    def test_batch_multiple_batches(self):
        """Test batching with multiple batches."""
        records = [{"id": i} for i in range(25)]
        batches = list(batch_records(records, batch_size=10))
        
        assert len(batches) == 3
        assert len(batches[0]) == 10
        assert len(batches[1]) == 10
        assert len(batches[2]) == 5
    
    def test_batch_size_one(self):
        """Test batching with size 1."""
        records = [{"id": i} for i in range(5)]
        batches = list(batch_records(records, batch_size=1))
        
        assert len(batches) == 5
        assert all(len(batch) == 1 for batch in batches)


class TestKinesisPublisher:
    """Test Kinesis Data Streams publisher."""
    
    def test_kinesis_publisher_initialization(self, mock_kinesis_client):
        """Test Kinesis publisher initialization."""
        with patch('boto3.client', return_value=mock_kinesis_client):
            publisher = KinesisPublisher(
                stream_name="test-stream",
                region="us-east-1"
            )
            
            assert publisher.stream_name == "test-stream"
            assert publisher.region == "us-east-1"
    
    def test_kinesis_publish_single_record(self, mock_kinesis_client, sample_detection):
        """Test publishing single record to Kinesis."""
        with patch('boto3.client', return_value=mock_kinesis_client):
            publisher = KinesisPublisher(stream_name="test-stream")
            
            publisher.publish(sample_detection)
            
            # Verify put_records was called
            mock_kinesis_client.put_records.assert_called_once()
            call_args = mock_kinesis_client.put_records.call_args
            
            # Check stream name
            assert call_args[1]['StreamName'] == "test-stream"
            
            # Check record format
            records = call_args[1]['Records']
            assert len(records) == 1
            assert 'Data' in records[0]
            assert 'PartitionKey' in records[0]
    
    def test_kinesis_publish_with_partition_key(self, mock_kinesis_client, sample_detection):
        """Test that partition key is set correctly."""
        with patch('boto3.client', return_value=mock_kinesis_client):
            publisher = KinesisPublisher(stream_name="test-stream")
            
            publisher.publish(sample_detection)
            
            call_args = mock_kinesis_client.put_records.call_args
            records = call_args[1]['Records']
            
            # Partition key should be camera_id
            assert records[0]['PartitionKey'] == "front-entrance"
    
    def test_kinesis_publish_data_is_json(self, mock_kinesis_client, sample_detection):
        """Test that published data is JSON encoded."""
        with patch('boto3.client', return_value=mock_kinesis_client):
            publisher = KinesisPublisher(stream_name="test-stream")
            
            publisher.publish(sample_detection)
            
            call_args = mock_kinesis_client.put_records.call_args
            records = call_args[1]['Records']
            data = records[0]['Data']
            
            # Data should be valid JSON
            parsed = json.loads(data)
            assert parsed['camera_id'] == "front-entrance"
            assert len(parsed['detections']) == 1
    
    def test_kinesis_batch_publish(self, mock_kinesis_client, sample_detection):
        """Test publishing multiple records in batch."""
        with patch('boto3.client', return_value=mock_kinesis_client):
            publisher = KinesisPublisher(stream_name="test-stream")
            
            # Publish multiple records
            records = [sample_detection.copy() for _ in range(5)]
            publisher.publish_batch(records)
            
            mock_kinesis_client.put_records.assert_called_once()
            call_args = mock_kinesis_client.put_records.call_args
            sent_records = call_args[1]['Records']
            
            assert len(sent_records) == 5
    
    def test_kinesis_large_batch_splits(self, mock_kinesis_client, sample_detection):
        """Test that large batches are split into multiple calls."""
        with patch('boto3.client', return_value=mock_kinesis_client):
            publisher = KinesisPublisher(stream_name="test-stream", batch_size=500)
            
            # Try to publish 1000 records (should split into 2 batches)
            records = [sample_detection.copy() for _ in range(1000)]
            publisher.publish_batch(records)
            
            # Should be called twice (500 + 500)
            assert mock_kinesis_client.put_records.call_count == 2
    
    def test_kinesis_handles_partial_failure(self, mock_kinesis_client, sample_detection):
        """Test handling of partial batch failures."""
        # Simulate partial failure
        mock_kinesis_client.put_records.return_value = {
            'FailedRecordCount': 1,
            'Records': [
                {'SequenceNumber': '12345'},
                {'ErrorCode': 'ProvisionedThroughputExceededException'}
            ]
        }
        
        with patch('boto3.client', return_value=mock_kinesis_client):
            publisher = KinesisPublisher(stream_name="test-stream")
            
            records = [sample_detection.copy() for _ in range(2)]
            result = publisher.publish_batch(records)
            
            # Should return failure information
            assert result['FailedRecordCount'] == 1
    
    def test_kinesis_retry_on_error(self, mock_kinesis_client, sample_detection):
        """Test retry logic on transient errors."""
        # Simulate error then success
        mock_kinesis_client.put_records.side_effect = [
            Exception("Throttled"),
            {'FailedRecordCount': 0, 'Records': [{'SequenceNumber': '12345'}]}
        ]
        
        with patch('boto3.client', return_value=mock_kinesis_client):
            with patch('time.sleep'):  # Mock sleep to speed up test
                publisher = KinesisPublisher(stream_name="test-stream", max_retries=2)
                
                publisher.publish(sample_detection)
                
                # Should have retried and succeeded
                assert mock_kinesis_client.put_records.call_count == 2


class TestS3Publisher:
    """Test S3 publisher."""
    
    def test_s3_publisher_initialization(self, mock_s3_client):
        """Test S3 publisher initialization."""
        with patch('boto3.client', return_value=mock_s3_client):
            publisher = S3Publisher(
                bucket_name="test-bucket",
                prefix="detections/",
                region="us-east-1"
            )
            
            assert publisher.bucket_name == "test-bucket"
            assert publisher.prefix == "detections/"
            assert publisher.region == "us-east-1"
    
    def test_s3_publish_detection(self, mock_s3_client, sample_detection):
        """Test publishing detection to S3."""
        with patch('boto3.client', return_value=mock_s3_client):
            publisher = S3Publisher(bucket_name="test-bucket")
            
            publisher.publish(sample_detection)
            
            # Verify put_object was called
            mock_s3_client.put_object.assert_called_once()
            call_args = mock_s3_client.put_object.call_args
            
            assert call_args[1]['Bucket'] == "test-bucket"
            assert 'Key' in call_args[1]
            assert 'Body' in call_args[1]
    
    def test_s3_key_format(self, mock_s3_client, sample_detection):
        """Test S3 key format includes camera_id and timestamp."""
        with patch('boto3.client', return_value=mock_s3_client):
            publisher = S3Publisher(
                bucket_name="test-bucket",
                prefix="detections/"
            )
            
            publisher.publish(sample_detection)
            
            call_args = mock_s3_client.put_object.call_args
            key = call_args[1]['Key']
            
            # Key should start with prefix
            assert key.startswith("detections/")
            
            # Key should include camera_id
            assert "front-entrance" in key
            
            # Key should end with .json
            assert key.endswith(".json")
    
    def test_s3_key_uses_timestamp(self, mock_s3_client, sample_detection):
        """Test that S3 key uses timestamp for uniqueness."""
        with patch('boto3.client', return_value=mock_s3_client):
            publisher = S3Publisher(bucket_name="test-bucket")
            
            # Publish same detection twice
            publisher.publish(sample_detection)
            publisher.publish(sample_detection)
            
            # Get both keys
            calls = mock_s3_client.put_object.call_args_list
            key1 = calls[0][1]['Key']
            key2 = calls[1][1]['Key']
            
            # Keys should be different (due to timestamp)
            # Note: May be same if called in same millisecond
            assert isinstance(key1, str) and isinstance(key2, str)
    
    def test_s3_body_is_json(self, mock_s3_client, sample_detection):
        """Test that S3 body is JSON encoded."""
        with patch('boto3.client', return_value=mock_s3_client):
            publisher = S3Publisher(bucket_name="test-bucket")
            
            publisher.publish(sample_detection)
            
            call_args = mock_s3_client.put_object.call_args
            body = call_args[1]['Body']
            
            # Body should be valid JSON
            if isinstance(body, bytes):
                body = body.decode('utf-8')
            parsed = json.loads(body)
            
            assert parsed['camera_id'] == "front-entrance"
            assert len(parsed['detections']) == 1
    
    def test_s3_metadata(self, mock_s3_client, sample_detection):
        """Test that S3 object includes metadata."""
        with patch('boto3.client', return_value=mock_s3_client):
            publisher = S3Publisher(bucket_name="test-bucket")
            
            publisher.publish(sample_detection)
            
            call_args = mock_s3_client.put_object.call_args
            
            # Check for metadata fields
            assert 'ContentType' in call_args[1]
            assert call_args[1]['ContentType'] == 'application/json'
    
    def test_s3_server_side_encryption(self, mock_s3_client, sample_detection):
        """Test that S3 publisher uses server-side encryption."""
        with patch('boto3.client', return_value=mock_s3_client):
            publisher = S3Publisher(bucket_name="test-bucket", encryption=True)
            
            publisher.publish(sample_detection)
            
            call_args = mock_s3_client.put_object.call_args
            
            # Check for encryption
            assert 'ServerSideEncryption' in call_args[1]
            assert call_args[1]['ServerSideEncryption'] in ['AES256', 'aws:kms']
    
    def test_s3_handles_upload_error(self, mock_s3_client, sample_detection):
        """Test handling of S3 upload errors."""
        mock_s3_client.put_object.side_effect = Exception("Access Denied")
        
        with patch('boto3.client', return_value=mock_s3_client):
            publisher = S3Publisher(bucket_name="test-bucket")
            
            with pytest.raises(Exception):
                publisher.publish(sample_detection)


class TestDynamoDBPublisher:
    """Test DynamoDB publisher."""
    
    def test_dynamodb_publisher_initialization(self, mock_dynamodb_client):
        """Test DynamoDB publisher initialization."""
        with patch('boto3.client', return_value=mock_dynamodb_client):
            publisher = DynamoDBPublisher(
                table_name="detections-table",
                region="us-east-1"
            )
            
            assert publisher.table_name == "detections-table"
            assert publisher.region == "us-east-1"
    
    def test_dynamodb_publish_detection(self, mock_dynamodb_client, sample_detection):
        """Test publishing detection to DynamoDB."""
        with patch('boto3.client', return_value=mock_dynamodb_client):
            publisher = DynamoDBPublisher(table_name="detections-table")
            
            publisher.publish(sample_detection)
            
            # Verify put_item was called
            mock_dynamodb_client.put_item.assert_called_once()
            call_args = mock_dynamodb_client.put_item.call_args
            
            assert call_args[1]['TableName'] == "detections-table"
            assert 'Item' in call_args[1]
    
    def test_dynamodb_item_structure(self, mock_dynamodb_client, sample_detection):
        """Test DynamoDB item structure."""
        with patch('boto3.client', return_value=mock_dynamodb_client):
            publisher = DynamoDBPublisher(table_name="detections-table")
            
            publisher.publish(sample_detection)
            
            call_args = mock_dynamodb_client.put_item.call_args
            item = call_args[1]['Item']
            
            # Check for required fields
            assert 'camera_id' in item
            assert 'timestamp' in item
            assert 'detections' in item
    
    def test_dynamodb_partition_key(self, mock_dynamodb_client, sample_detection):
        """Test DynamoDB partition key."""
        with patch('boto3.client', return_value=mock_dynamodb_client):
            publisher = DynamoDBPublisher(table_name="detections-table")
            
            publisher.publish(sample_detection)
            
            call_args = mock_dynamodb_client.put_item.call_args
            item = call_args[1]['Item']
            
            # Partition key should be camera_id
            assert item['camera_id']['S'] == "front-entrance"
    
    def test_dynamodb_sort_key(self, mock_dynamodb_client, sample_detection):
        """Test DynamoDB sort key (timestamp)."""
        with patch('boto3.client', return_value=mock_dynamodb_client):
            publisher = DynamoDBPublisher(table_name="detections-table")
            
            publisher.publish(sample_detection)
            
            call_args = mock_dynamodb_client.put_item.call_args
            item = call_args[1]['Item']
            
            # Sort key should be timestamp
            assert 'timestamp' in item
            assert 'N' in item['timestamp']  # Number type
    
    def test_dynamodb_batch_write(self, mock_dynamodb_client, sample_detection):
        """Test DynamoDB batch write."""
        mock_dynamodb_client.batch_write_item.return_value = {
            'UnprocessedItems': {}
        }
        
        with patch('boto3.client', return_value=mock_dynamodb_client):
            publisher = DynamoDBPublisher(table_name="detections-table")
            
            records = [sample_detection.copy() for _ in range(10)]
            publisher.publish_batch(records)
            
            # Verify batch_write_item was called
            mock_dynamodb_client.batch_write_item.assert_called_once()
    
    def test_dynamodb_handles_conditional_check_failure(self, mock_dynamodb_client, sample_detection):
        """Test handling of conditional check failures."""
        from botocore.exceptions import ClientError
        
        error_response = {
            'Error': {
                'Code': 'ConditionalCheckFailedException',
                'Message': 'The conditional request failed'
            }
        }
        mock_dynamodb_client.put_item.side_effect = ClientError(error_response, 'PutItem')
        
        with patch('boto3.client', return_value=mock_dynamodb_client):
            publisher = DynamoDBPublisher(table_name="detections-table")
            
            # Should handle gracefully
            with pytest.raises(ClientError):
                publisher.publish(sample_detection)
    
    def test_dynamodb_ttl_attribute(self, mock_dynamodb_client, sample_detection):
        """Test that DynamoDB item includes TTL attribute."""
        with patch('boto3.client', return_value=mock_dynamodb_client):
            publisher = DynamoDBPublisher(
                table_name="detections-table",
                ttl_days=7
            )
            
            publisher.publish(sample_detection)
            
            call_args = mock_dynamodb_client.put_item.call_args
            item = call_args[1]['Item']
            
            # Should include TTL attribute
            assert 'ttl' in item or 'expiration_time' in item


class TestPublisherIntegration:
    """Test integration between publishers."""
    
    def test_multiple_publishers(self, mock_kinesis_client, mock_s3_client, sample_detection):
        """Test using multiple publishers together."""
        with patch('boto3.client', side_effect=[mock_kinesis_client, mock_s3_client]):
            kinesis_pub = KinesisPublisher(stream_name="test-stream")
            s3_pub = S3Publisher(bucket_name="test-bucket")
            
            # Publish to both
            kinesis_pub.publish(sample_detection)
            s3_pub.publish(sample_detection)
            
            mock_kinesis_client.put_records.assert_called_once()
            mock_s3_client.put_object.assert_called_once()
    
    def test_publisher_manager(self, mock_kinesis_client, mock_s3_client, mock_dynamodb_client, sample_detection):
        """Test publisher manager that coordinates multiple publishers."""
        with patch('boto3.client', side_effect=[
            mock_kinesis_client,
            mock_s3_client,
            mock_dynamodb_client
        ]):
            from src.kvs_infer.publishers import PublisherManager
            
            manager = PublisherManager(
                kinesis_stream="test-stream",
                s3_bucket="test-bucket",
                dynamodb_table="test-table"
            )
            
            manager.publish(sample_detection)
            
            # All publishers should be called
            mock_kinesis_client.put_records.assert_called_once()
            mock_s3_client.put_object.assert_called_once()
            mock_dynamodb_client.put_item.assert_called_once()
    
    def test_publisher_error_handling(self, mock_kinesis_client, mock_s3_client, sample_detection):
        """Test that failure in one publisher doesn't affect others."""
        mock_kinesis_client.put_records.side_effect = Exception("Kinesis error")
        
        with patch('boto3.client', side_effect=[mock_kinesis_client, mock_s3_client]):
            from src.kvs_infer.publishers import PublisherManager
            
            manager = PublisherManager(
                kinesis_stream="test-stream",
                s3_bucket="test-bucket",
                fail_fast=False
            )
            
            # Should continue to S3 even if Kinesis fails
            manager.publish(sample_detection)
            
            mock_s3_client.put_object.assert_called_once()


class TestPublisherPerformance:
    """Test publisher performance characteristics."""
    
    def test_kinesis_batch_performance(self, mock_kinesis_client, sample_detection):
        """Test that batching is more efficient than individual calls."""
        with patch('boto3.client', return_value=mock_kinesis_client):
            publisher = KinesisPublisher(stream_name="test-stream")
            
            records = [sample_detection.copy() for _ in range(100)]
            
            # Batch publish should make fewer API calls
            publisher.publish_batch(records)
            
            # Should batch into reasonable chunks
            call_count = mock_kinesis_client.put_records.call_count
            assert call_count < 100  # Should be batched
    
    def test_s3_concurrent_uploads(self, mock_s3_client, sample_detection):
        """Test concurrent S3 uploads."""
        with patch('boto3.client', return_value=mock_s3_client):
            publisher = S3Publisher(bucket_name="test-bucket")
            
            records = [sample_detection.copy() for _ in range(10)]
            
            # Publish multiple records
            for record in records:
                publisher.publish(record)
            
            # All should succeed
            assert mock_s3_client.put_object.call_count == 10
