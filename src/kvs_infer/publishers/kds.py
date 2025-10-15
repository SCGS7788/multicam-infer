"""
Publish detection events to Kinesis Data Streams.
"""

import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import boto3
from botocore.exceptions import ClientError


logger = logging.getLogger(__name__)


class KinesisDataStreamPublisher:
    """
    Publish detection events to Kinesis Data Streams.
    
    Events are JSON-encoded and sent as records to a Kinesis stream.
    """
    
    def __init__(
        self,
        stream_name: str,
        region: str = "us-east-1",
        partition_key_field: str = "camera_name",
    ):
        """
        Initialize Kinesis Data Streams publisher.
        
        Args:
            stream_name: Name of the Kinesis Data Stream
            region: AWS region
            partition_key_field: Field to use as partition key (for distribution)
        """
        self.stream_name = stream_name
        self.region = region
        self.partition_key_field = partition_key_field
        
        self.client = boto3.client("kinesis", region_name=region)
        
        logger.info(
            f"Initialized Kinesis publisher for stream: {stream_name} "
            f"in region: {region}"
        )
    
    def publish_event(
        self,
        event: Dict[str, Any],
        partition_key: Optional[str] = None,
    ) -> bool:
        """
        Publish a detection event to Kinesis Data Stream.
        
        Args:
            event: Event data as dictionary
            partition_key: Optional partition key override
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Use provided partition key or extract from event
            if partition_key is None:
                partition_key = event.get(
                    self.partition_key_field,
                    "default"
                )
            
            # Add timestamp if not present
            if "timestamp" not in event:
                event["timestamp"] = datetime.utcnow().isoformat()
            
            # Convert to JSON
            data = json.dumps(event)
            
            # Send to Kinesis
            response = self.client.put_record(
                StreamName=self.stream_name,
                Data=data,
                PartitionKey=partition_key,
            )
            
            logger.debug(
                f"Published event to Kinesis. "
                f"Shard: {response['ShardId']}, "
                f"Sequence: {response['SequenceNumber']}"
            )
            
            return True
        
        except ClientError as e:
            logger.error(
                f"Failed to publish event to Kinesis: {e}",
                exc_info=True
            )
            return False
        
        except Exception as e:
            logger.error(
                f"Unexpected error publishing to Kinesis: {e}",
                exc_info=True
            )
            return False
    
    def publish_batch(
        self,
        events: list[Dict[str, Any]],
    ) -> tuple[int, int]:
        """
        Publish multiple events in a batch.
        
        Args:
            events: List of event dictionaries
            
        Returns:
            Tuple of (successful_count, failed_count)
        """
        if not events:
            return 0, 0
        
        try:
            records = []
            for event in events:
                # Extract partition key
                partition_key = event.get(
                    self.partition_key_field,
                    "default"
                )
                
                # Add timestamp if not present
                if "timestamp" not in event:
                    event["timestamp"] = datetime.utcnow().isoformat()
                
                records.append({
                    "Data": json.dumps(event),
                    "PartitionKey": partition_key,
                })
            
            # Send batch (max 500 records per request)
            success_count = 0
            fail_count = 0
            
            for i in range(0, len(records), 500):
                batch = records[i:i+500]
                
                response = self.client.put_records(
                    StreamName=self.stream_name,
                    Records=batch,
                )
                
                success_count += len(batch) - response["FailedRecordCount"]
                fail_count += response["FailedRecordCount"]
                
                if response["FailedRecordCount"] > 0:
                    logger.warning(
                        f"Batch had {response['FailedRecordCount']} failed records"
                    )
            
            logger.info(
                f"Published batch: {success_count} successful, {fail_count} failed"
            )
            
            return success_count, fail_count
        
        except Exception as e:
            logger.error(
                f"Failed to publish batch to Kinesis: {e}",
                exc_info=True
            )
            return 0, len(events)
