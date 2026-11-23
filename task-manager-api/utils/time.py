from datetime import datetime, timezone


def utc_now():
    """UTC atual como datetime naive (mesmo formato/semântica do antigo datetime.utcnow())."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
