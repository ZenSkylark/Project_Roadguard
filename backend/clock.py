from datetime import datetime, timezone

def utcnow() -> datetime:
    """
    Returns current UTC time as a naive datetime (no timezone info).
    
    Python 3.12 deprecates datetime.utcnow(), but SQLite stores naive timestamps.
    This helper uses the modern aware API then strips tzinfo for compatibility.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)