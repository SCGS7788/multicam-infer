"""
Kinesis Data Stream publisher with batching, retries, and exponential backoff.
"""

import logging
import time
import random
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from collections import deque
import json

import boto3
from botocore.exceptions import ClientError


logger = logging.getLogger(__name__)


def _generate_event_id(camera_id: str, event_type: str, label: str, ts_ms: int) -> str:
    """
    Generate deterministic event ID using SHA1 hash.
    
    Buckets timestamp to 1-second intervals to allow deduplication.
    
    Args:
        camera_id: Camera identifier
        event_type: Event type (weapon, fire, smoke, alpr)
        label: Detection label
        ts_ms: Timestamp in milliseconds
        
    Returns:
        SHA1 hash (40 characters)
    """
    # Bucket timestamp to 1-second intervals
    ts_bucket = ts_ms // 1000
    
    hash_input = f"{camera_id}:{event_type}:{label}:{ts_bucket}"
    return hashlib.sha1(hash_input.encode()).hexdigest()


def _create_event_envelope(event: Dict[str, Any], producer_version: str = "kvs-infer/1.0") -> Dict[str, Any]:
    """
    Wrap event in standard envelope with event_id and metadata.
    
    Args:
        event: Raw event dict from detector
        producer_version: Producer version string
        
    Returns:
        Event envelope
    """
    event_id = _generate_event_id(
        camera_id=event["camera_id"],
        event_type=event["type"],
        label=event["label"],
        ts_ms=event["ts_ms"]
    )
    
    envelope = {
        "event_id": event_id,
        "camera_id": event["camera_id"],
        "producer": producer_version,
        "payload": event
    }
    
    return envelope


class KDSClient:
    """
    Kinesis Data Stream client with batching, retries, and exponential backoff.
    
    Features:
    - Automatic batching (up to 500 records or 5 MB per request)
    - Exponential backoff with jitter (80-120%)
    - Retry logic for throttling and transient errors
    - Structured logging for success/failure
    - Metrics tracking (published, failed, retried)
    
    Configuration:
        region: AWS region (e.g., "us-east-1")
        stream_name: Kinesis Data Stream name
        batch_size: Max records per batch (default: 500)
        max_retries: Max retry attempts (default: 3)
        base_backoff_ms: Base backoff in milliseconds (default: 100)
        producer_version: Producer version string (default: "kvs-infer/1.0")
        
    Example:
        client = KDSClient(region="us-east-1", stream_name="events-stream")
        
        # Single event
        client.put_event(event_dict, partition_key="camera_1")
        
        # Batch events
        client.put_events([event1, event2, event3], partition_key="camera_1")
        
        # Flush pending events
        client.flush()
    """
    
    def __init__(
        self,
        region: str,
        stream_name: str,
        batch_size: int = 500,
        max_retries: int = 3,
        base_backoff_ms: int = 100,
        producer_version: str = "kvs-infer/1.0"
    ):
        """
        Initialize KDS client.
        
        Args:
            region: AWS region
            stream_name: Kinesis Data Stream name
            batch_size: Max records per batch (1-500)
            max_retries: Max retry attempts
            base_backoff_ms: Base backoff in milliseconds
            producer_version: Producer version string
        """
        self.region = region
        self.stream_name = stream_name
        self.batch_size = min(batch_size, 500)  # AWS limit
        self.max_retries = max_retries
        self.base_backoff_ms = base_backoff_ms
        self.producer_version = producer_version
        
        # Initialize boto3 client
        self.client = boto3.client('kinesis', region_name=region)
        
        # Batch buffer
        self._batch_buffer: List[Tuple[Dict[str, Any], str]] = []
        
        # Metrics
        self.metrics = {
            "published": 0,
            "failed": 0,
            "retried": 0,
            "batches_sent": 0,
        }
        
        logger.info(
            f"KDS client initialized: region={region}, stream={stream_name}, "
            f"batch_size={self.batch_size}"
        )
    
    def put_event(self, event: Dict[str, Any], partition_key: str) -> bool:
        """
        Publish single event to Kinesis Data Stream.
        
        Wraps event in envelope and adds to batch buffer.
        Flushes batch if buffer reaches batch_size.
        
        Args:
            event: Event dict from detector
            partition_key: Partition key (typically camera_id)
            
        Returns:
            True if successfully added to buffer
        """
        # Wrap in envelope
        envelope = _create_event_envelope(event, self.producer_version)
        
        # Add to batch buffer
        self._batch_buffer.append((envelope, partition_key))
        
        # Flush if buffer full
        if len(self._batch_buffer) >= self.batch_size:
            return self.flush()
        
        return True
    
    def put_events(self, events: List[Dict[str, Any]], partition_key: str) -> bool:
        """
        Publish multiple events to Kinesis Data Stream.
        
        Args:
            events: List of event dicts
            partition_key: Partition key for all events
            
        Returns:
            True if all events successfully published
        """
        success = True
        
        for event in events:
            if not self.put_event(event, partition_key):
                success = False
        
        # Flush remaining
        if not self.flush():
            success = False
        
        return success
    
    def flush(self) -> bool:
        """
        Flush pending events in batch buffer.
        
        Returns:
            True if all events successfully published
        """
        if not self._batch_buffer:
            return True
        
        # Prepare batch
        batch = self._batch_buffer.copy()
        self._batch_buffer.clear()
        
        # Send batch with retries
        return self._send_batch_with_retries(batch)
    
    def _send_batch_with_retries(self, batch: List[Tuple[Dict[str, Any], str]]) -> bool:
        """
        Send batch with exponential backoff and jitter.
        
        Args:
            batch: List of (envelope, partition_key) tuples
            
        Returns:
            True if all records successfully published
        """
        records = [
            {
                "Data": json.dumps(envelope),
                "PartitionKey": partition_key
            }
            for envelope, partition_key in batch
        ]
        
        attempt = 0
        failed_records = records
        
        while attempt <= self.max_retries and failed_records:
            try:
                # Send batch
                response = self.client.put_records(
                    Records=failed_records,
                    StreamName=self.stream_name
                )
                
                # Check for failures
                failed_count = response.get('FailedRecordCount', 0)
                
                if failed_count == 0:
                    # All succeeded
                    success_count = len(failed_records)
                    self.metrics["published"] += success_count
                    self.metrics["batches_sent"] += 1
                    
                    logger.info(
                        f"KDS batch published: {success_count} records, "
                        f"stream={self.stream_name}",
                        extra={
                            "stream_name": self.stream_name,
                            "record_count": success_count,
                            "attempt": attempt
                        }
                    )
                    
                    return True
                
                # Extract failed records for retry
                new_failed_records = []
                for i, record_result in enumerate(response['Records']):
                    if 'ErrorCode' in record_result:
                        new_failed_records.append(failed_records[i])
                        
                        logger.warning(
                            f"KDS record failed: {record_result['ErrorCode']} - "
                            f"{record_result.get('ErrorMessage', 'Unknown error')}",
                            extra={
                                "error_code": record_result['ErrorCode'],
                                "error_message": record_result.get('ErrorMessage', ''),
                                "attempt": attempt
                            }
                        )
                
                # Update metrics
                success_count = len(failed_records) - len(new_failed_records)
                self.metrics["published"] += success_count
                self.metrics["failed"] += len(new_failed_records)
                
                failed_records = new_failed_records
                
                if failed_records and attempt < self.max_retries:
                    # Exponential backoff with jitter
                    backoff_ms = self.base_backoff_ms * (2 ** attempt)
                    jitter = random.uniform(0.8, 1.2)
                    sleep_ms = backoff_ms * jitter
                    
                    logger.info(
                        f"Retrying KDS batch: {len(failed_records)} records, "
                        f"backoff={sleep_ms:.0f}ms",
                        extra={
                            "failed_count": len(failed_records),
                            "backoff_ms": sleep_ms,
                            "attempt": attempt + 1
                        }
                    )
                    
                    time.sleep(sleep_ms / 1000.0)
                    self.metrics["retried"] += len(failed_records)
                
            except ClientError as e:
                error_code = e.response['Error']['Code']
                error_message = e.response['Error']['Message']
                
                logger.error(
                    f"KDS client error: {error_code} - {error_message}",
                    extra={
                        "error_code": error_code,
                        "error_message": error_message,
                        "attempt": attempt,
                        "record_count": len(failed_records)
                    },
                    exc_info=True
                )
                
                # Retry on throttling or transient errors
                if error_code in ['ProvisionedThroughputExceededException', 'ServiceUnavailable']:
                    if attempt < self.max_retries:
                        backoff_ms = self.base_backoff_ms * (2 ** attempt)
                        jitter = random.uniform(0.8, 1.2)
                        sleep_ms = backoff_ms * jitter
                        
                        time.sleep(sleep_ms / 1000.0)
                        self.metrics["retried"] += len(failed_records)
                else:
                    # Non-retryable error
                    self.metrics["failed"] += len(failed_records)
                    return False
            
            except Exception as e:
                logger.error(
                    f"Unexpected error publishing to KDS: {e}",
                    extra={
                        "attempt": attempt,
                        "record_count": len(failed_records)
                    },
                    exc_info=True
                )
                
                self.metrics["failed"] += len(failed_records)
                return False
            
            attempt += 1
        
        # Max retries exceeded
        if failed_records:
            logger.error(
                f"KDS batch failed after {self.max_retries} retries: "
                f"{len(failed_records)} records lost",
                extra={
                    "failed_count": len(failed_records),
                    "max_retries": self.max_retries
                }
            )
            
            return False
        
        return True
    
    def get_metrics(self) -> Dict[str, int]:
        """
        Get publisher metrics.
        
        Returns:
            Metrics dict with published, failed, retried, batches_sent counts
        """
        return self.metrics.copy()
    
    def reset_metrics(self):
        """Reset metrics counters."""
        self.metrics = {
            "published": 0,
            "failed": 0,
            "retried": 0,
            "batches_sent": 0,
        }
        
        logger.info("KDS metrics reset")
