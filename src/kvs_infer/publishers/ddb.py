"""
Write detection metadata to DynamoDB (optional).
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from decimal import Decimal
import boto3
from botocore.exceptions import ClientError


logger = logging.getLogger(__name__)


class DynamoDBPublisher:
    """
    Write detection metadata to DynamoDB.
    
    Useful for:
    - Queryable detection history
    - Audit trails
    - Analytics and reporting
    """
    
    def __init__(
        self,
        table_name: str,
        region: str = "us-east-1",
    ):
        """
        Initialize DynamoDB publisher.
        
        Args:
            table_name: DynamoDB table name
            region: AWS region
        """
        self.table_name = table_name
        self.region = region
        
        self.dynamodb = boto3.resource("dynamodb", region_name=region)
        self.table = self.dynamodb.Table(table_name)
        
        logger.info(
            f"Initialized DynamoDB publisher for table: {table_name} "
            f"in region: {region}"
        )
    
    def _convert_floats_to_decimal(self, obj: Any) -> Any:
        """
        Recursively convert float to Decimal (required by DynamoDB).
        
        Args:
            obj: Object to convert
            
        Returns:
            Converted object
        """
        if isinstance(obj, float):
            return Decimal(str(obj))
        elif isinstance(obj, dict):
            return {k: self._convert_floats_to_decimal(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_floats_to_decimal(v) for v in obj]
        else:
            return obj
    
    def write_detection(
        self,
        item: Dict[str, Any],
    ) -> bool:
        """
        Write a detection record to DynamoDB.
        
        Expected item structure:
        {
            "camera_name": str,        # Partition key
            "timestamp": str (ISO),    # Sort key
            "detector_type": str,
            "detections": [...],
            "s3_snapshot_key": str (optional),
            ... other metadata ...
        }
        
        Args:
            item: Detection item to write
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Add timestamp if not present
            if "timestamp" not in item:
                item["timestamp"] = datetime.utcnow().isoformat()
            
            # Convert floats to Decimal
            item = self._convert_floats_to_decimal(item)
            
            # Write to DynamoDB
            self.table.put_item(Item=item)
            
            logger.debug(
                f"Wrote detection to DynamoDB: "
                f"{item.get('camera_name')}/{item.get('timestamp')}"
            )
            
            return True
        
        except ClientError as e:
            logger.error(
                f"Failed to write to DynamoDB: {e}",
                exc_info=True
            )
            return False
        
        except Exception as e:
            logger.error(
                f"Unexpected error writing to DynamoDB: {e}",
                exc_info=True
            )
            return False
    
    def write_batch(
        self,
        items: list[Dict[str, Any]],
    ) -> tuple[int, int]:
        """
        Write multiple detection records in a batch.
        
        Args:
            items: List of detection items
            
        Returns:
            Tuple of (successful_count, failed_count)
        """
        if not items:
            return 0, 0
        
        try:
            success_count = 0
            fail_count = 0
            
            # Batch write (max 25 items per request)
            with self.table.batch_writer() as batch:
                for item in items:
                    try:
                        # Add timestamp if not present
                        if "timestamp" not in item:
                            item["timestamp"] = datetime.utcnow().isoformat()
                        
                        # Convert floats to Decimal
                        item = self._convert_floats_to_decimal(item)
                        
                        batch.put_item(Item=item)
                        success_count += 1
                    
                    except Exception as e:
                        logger.error(f"Failed to add item to batch: {e}")
                        fail_count += 1
            
            logger.info(
                f"Wrote batch to DynamoDB: {success_count} successful, "
                f"{fail_count} failed"
            )
            
            return success_count, fail_count
        
        except Exception as e:
            logger.error(
                f"Failed to write batch to DynamoDB: {e}",
                exc_info=True
            )
            return 0, len(items)
    
    def query_by_camera(
        self,
        camera_name: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 100,
    ) -> list[Dict[str, Any]]:
        """
        Query detections for a specific camera.
        
        Args:
            camera_name: Camera name (partition key)
            start_time: Start timestamp (ISO format)
            end_time: End timestamp (ISO format)
            limit: Maximum number of items to return
            
        Returns:
            List of detection items
        """
        try:
            query_params = {
                "KeyConditionExpression": "camera_name = :camera_name",
                "ExpressionAttributeValues": {
                    ":camera_name": camera_name,
                },
                "Limit": limit,
                "ScanIndexForward": False,  # Most recent first
            }
            
            # Add time range if provided
            if start_time and end_time:
                query_params["KeyConditionExpression"] += " AND #ts BETWEEN :start AND :end"
                query_params["ExpressionAttributeNames"] = {"#ts": "timestamp"}
                query_params["ExpressionAttributeValues"].update({
                    ":start": start_time,
                    ":end": end_time,
                })
            elif start_time:
                query_params["KeyConditionExpression"] += " AND #ts >= :start"
                query_params["ExpressionAttributeNames"] = {"#ts": "timestamp"}
                query_params["ExpressionAttributeValues"][":start"] = start_time
            elif end_time:
                query_params["KeyConditionExpression"] += " AND #ts <= :end"
                query_params["ExpressionAttributeNames"] = {"#ts": "timestamp"}
                query_params["ExpressionAttributeValues"][":end"] = end_time
            
            response = self.table.query(**query_params)
            
            return response.get("Items", [])
        
        except Exception as e:
            logger.error(f"Failed to query DynamoDB: {e}", exc_info=True)
            return []
