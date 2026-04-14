from datetime import datetime, timezone


def parse_expiration_date(expiration_date_str: str) -> datetime:
    """Parse ISO datetime string and normalize to UTC.
    Raises:
        ValueError: If the input cannot be parsed as ISO datetime.
    """
    expiration_date = datetime.fromisoformat(expiration_date_str)
    if expiration_date.tzinfo is None:
        return expiration_date.replace(tzinfo=timezone.utc)
    return expiration_date.astimezone(timezone.utc)
