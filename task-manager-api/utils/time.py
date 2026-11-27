from datetime import datetime, timezone


def utc_now():
    """UTC atual como datetime naive (mesmo formato que datetime.utcnow gravava)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
