"""
Time utilities.
"""

from datetime import datetime, timezone
from typing import Optional


def utc_now() -> datetime:
    """
    Get current UTC time as timezone-aware datetime.
    
    Returns:
        Current UTC datetime
    """
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    """
    Get current UTC time as ISO 8601 string.
    
    Returns:
        ISO 8601 formatted string
    """
    return utc_now().isoformat()


def timestamp_to_datetime(timestamp: float) -> datetime:
    """
    Convert Unix timestamp to timezone-aware datetime.
    
    Args:
        timestamp: Unix timestamp (seconds since epoch)
        
    Returns:
        Timezone-aware datetime in UTC
    """
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


def timestamp_to_iso(timestamp: float) -> str:
    """
    Convert Unix timestamp to ISO 8601 string.
    
    Args:
        timestamp: Unix timestamp (seconds since epoch)
        
    Returns:
        ISO 8601 formatted string
    """
    return timestamp_to_datetime(timestamp).isoformat()


def iso_to_datetime(iso_string: str) -> Optional[datetime]:
    """
    Parse ISO 8601 string to datetime.
    
    Args:
        iso_string: ISO 8601 formatted string
        
    Returns:
        Parsed datetime, or None if parsing fails
    """
    try:
        return datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        return None


def datetime_to_iso(dt: datetime) -> str:
    """
    Convert datetime to ISO 8601 string.
    
    Args:
        dt: Datetime object
        
    Returns:
        ISO 8601 formatted string
    """
    return dt.isoformat()


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable string.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted string (e.g., "1h 23m 45s")
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    
    minutes = int(seconds // 60)
    seconds = seconds % 60
    
    if minutes < 60:
        return f"{minutes}m {seconds:.0f}s"
    
    hours = minutes // 60
    minutes = minutes % 60
    
    return f"{hours}h {minutes}m {seconds:.0f}s"
