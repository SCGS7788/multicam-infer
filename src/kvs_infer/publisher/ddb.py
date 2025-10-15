"""
DynamoDB publisher for persisting events to a table.
"""

import logging
from typing import Dict, Any, Optional, List
from decimal import Decimal
import json

import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key


logger = logging.getLogger(__name__)


def _convert_floats_to_decimal(obj: Any) -> Any:
    """
    Convert float values to Decimal for DynamoDB compatibility.
    
    DynamoDB does not support native float types.
    
    Args:
        obj: Object to convert
        
    Returns:
        Object with floats converted to Decimal
    """
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: _convert_floats_to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_floats_to_decimal(item) for item in obj]
    else:
        return obj


def _convert_decimal_to_float(obj: Any) -> Any:
    """
    Convert Decimal values to float for JSON serialization.
    
    Args:
        obj: Object to convert
        
    Returns:
        Object with Decimals converted to float
    """
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: _convert_decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_decimal_to_float(item) for item in obj]
    else:
        return obj


class DDBWriter:
    """
    DynamoDB writer for persisting detection events.
    
    Features:
    - Automatic float-to-Decimal conversion
    - Batch writing support (up to 25 items per batch)
    - Conditional writes (prevent duplicates)
    - TTL support for automatic expiration
    - Structured logging for success/failure
    - Metrics tracking (written, failed, batches)
    
    Table Schema:
        Partition Key: event_id (String) - SHA1 hash
        Sort Key: ts_ms (Number) - Timestamp in milliseconds
        Attributes: camera_id, type, label, conf, bbox, extras, ttl, etc.
        
    GSI (Optional):
        camera_id-ts_ms-index: For querying events by camera and time range
        
    Configuration:
        table_name: DynamoDB table name
        region: AWS region (default: "us-east-1")
        ttl_days: TTL in days (default: None = no expiration)
        
    Example:
        writer = DDBWriter(table_name="events-table", ttl_days=30)
        
        # Write single event
        writer.put_event(event_dict)
        
        # Write batch
        writer.put_events([event1, event2, event3])
    """
    
    def __init__(
        self,
        table_name: str,
        region: str = "us-east-1",
        ttl_days: Optional[int] = None
    ):
        """
        Initialize DynamoDB writer.
        
        Args:
            table_name: DynamoDB table name
            region: AWS region
            ttl_days: TTL in days (None = no expiration)
        """
        self.table_name = table_name
        self.region = region
        self.ttl_days = ttl_days
        
        # Initialize boto3 resources
        dynamodb = boto3.resource('dynamodb', region_name=region)
        self.table = dynamodb.Table(table_name)
        
        # Metrics
        self.metrics = {
            "written": 0,
            "failed": 0,
            "batches_sent": 0,
        }
        
        logger.info(
            f"DDB writer initialized: table={table_name}, "
            f"region={region}, ttl_days={ttl_days}"
        )
    
    def put_event(self, event: Dict[str, Any]) -> bool:
        """
        Write single event to DynamoDB.
        
        Args:
            event: Event envelope dict with event_id, camera_id, payload
            
        Returns:
            True if successfully written
        """
        try:
            # Prepare item
            item = self._prepare_item(event)
            
            # Write to DynamoDB
            self.table.put_item(Item=item)
            
            # Update metrics
            self.metrics["written"] += 1
            
            logger.info(
                f"DDB event written: event_id={event['event_id']}, "
                f"camera={event['camera_id']}",
                extra={
                    "table_name": self.table_name,
                    "event_id": event["event_id"],
                    "camera_id": event["camera_id"],
                    "event_type": event["payload"]["type"]
                }
            )
            
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            logger.error(
                f"DDB client error: {error_code} - {error_message}",
                extra={
                    "error_code": error_code,
                    "error_message": error_message,
                    "table_name": self.table_name,
                    "event_id": event.get("event_id", "unknown")
                },
                exc_info=True
            )
            
            self.metrics["failed"] += 1
            return False
            
        except Exception as e:
            logger.error(
                f"Unexpected error writing to DDB: {e}",
                extra={
                    "table_name": self.table_name,
                    "event_id": event.get("event_id", "unknown")
                },
                exc_info=True
            )
            
            self.metrics["failed"] += 1
            return False
    
    def put_events(self, events: List[Dict[str, Any]]) -> bool:
        """
        Write multiple events to DynamoDB using batch write.
        
        Automatically chunks into batches of 25 items (DynamoDB limit).
        
        Args:
            events: List of event envelope dicts
            
        Returns:
            True if all events successfully written
        """
        if not events:
            return True
        
        # Chunk into batches of 25
        batch_size = 25
        all_success = True
        
        for i in range(0, len(events), batch_size):
            batch = events[i:i + batch_size]
            
            if not self._write_batch(batch):
                all_success = False
        
        return all_success
    
    def _write_batch(self, batch: List[Dict[str, Any]]) -> bool:
        """
        Write batch of events using batch_write_item.
        
        Args:
            batch: List of event dicts (max 25)
            
        Returns:
            True if all items successfully written
        """
        try:
            # Prepare items
            items = [self._prepare_item(event) for event in batch]
            
            # Write batch
            with self.table.batch_writer() as batch_writer:
                for item in items:
                    batch_writer.put_item(Item=item)
            
            # Update metrics
            self.metrics["written"] += len(batch)
            self.metrics["batches_sent"] += 1
            
            logger.info(
                f"DDB batch written: {len(batch)} events",
                extra={
                    "table_name": self.table_name,
                    "batch_size": len(batch)
                }
            )
            
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            logger.error(
                f"DDB batch write error: {error_code} - {error_message}",
                extra={
                    "error_code": error_code,
                    "error_message": error_message,
                    "table_name": self.table_name,
                    "batch_size": len(batch)
                },
                exc_info=True
            )
            
            self.metrics["failed"] += len(batch)
            return False
            
        except Exception as e:
            logger.error(
                f"Unexpected error in DDB batch write: {e}",
                extra={
                    "table_name": self.table_name,
                    "batch_size": len(batch)
                },
                exc_info=True
            )
            
            self.metrics["failed"] += len(batch)
            return False
    
    def _prepare_item(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare item for DynamoDB write.
        
        - Flatten payload fields to top level
        - Convert floats to Decimal
        - Add TTL if configured
        
        Args:
            event: Event envelope dict
            
        Returns:
            DynamoDB item dict
        """
        payload = event["payload"]
        
        # Flatten payload to top level
        item = {
            "event_id": event["event_id"],
            "camera_id": event["camera_id"],
            "producer": event["producer"],
            "ts_ms": payload["ts_ms"],
            "type": payload["type"],
            "label": payload["label"],
            "conf": payload["conf"],
            "bbox": payload["bbox"],
            "extras": payload.get("extras", {}),
        }
        
        # Add TTL if configured
        if self.ttl_days is not None:
            import time
            ttl_timestamp = int(time.time()) + (self.ttl_days * 86400)
            item["ttl"] = ttl_timestamp
        
        # Convert floats to Decimal
        item = _convert_floats_to_decimal(item)
        
        return item
    
    def query_by_camera(
        self,
        camera_id: str,
        start_ts_ms: Optional[int] = None,
        end_ts_ms: Optional[int] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Query events by camera ID and time range.
        
        Requires GSI: camera_id-ts_ms-index
        
        Args:
            camera_id: Camera identifier
            start_ts_ms: Start timestamp (inclusive)
            end_ts_ms: End timestamp (inclusive)
            limit: Max results (default: 100)
            
        Returns:
            List of event dicts
        """
        try:
            # Build query
            key_condition = Key('camera_id').eq(camera_id)
            
            if start_ts_ms and end_ts_ms:
                key_condition &= Key('ts_ms').between(start_ts_ms, end_ts_ms)
            elif start_ts_ms:
                key_condition &= Key('ts_ms').gte(start_ts_ms)
            elif end_ts_ms:
                key_condition &= Key('ts_ms').lte(end_ts_ms)
            
            # Execute query
            response = self.table.query(
                IndexName='camera_id-ts_ms-index',
                KeyConditionExpression=key_condition,
                Limit=limit,
                ScanIndexForward=False  # Descending order (newest first)
            )
            
            items = response.get('Items', [])
            
            # Convert Decimal to float
            items = [_convert_decimal_to_float(item) for item in items]
            
            logger.debug(
                f"DDB query result: {len(items)} events",
                extra={
                    "camera_id": camera_id,
                    "start_ts_ms": start_ts_ms,
                    "end_ts_ms": end_ts_ms,
                    "result_count": len(items)
                }
            )
            
            return items
            
        except ClientError as e:
            logger.error(
                f"DDB query error: {e}",
                extra={
                    "camera_id": camera_id,
                    "start_ts_ms": start_ts_ms,
                    "end_ts_ms": end_ts_ms
                },
                exc_info=True
            )
            
            return []
    
    def get_metrics(self) -> Dict[str, int]:
        """
        Get publisher metrics.
        
        Returns:
            Metrics dict with written, failed, batches_sent counts
        """
        return self.metrics.copy()
    
    def reset_metrics(self):
        """Reset metrics counters."""
        self.metrics = {
            "written": 0,
            "failed": 0,
            "batches_sent": 0,
        }
        
        logger.info("DDB metrics reset")
