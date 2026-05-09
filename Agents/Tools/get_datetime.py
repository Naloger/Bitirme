from __future__ import annotations

import datetime
from typing import Optional, Dict


def get_datetime(tz: Optional[datetime.tzinfo] = None) -> Dict[str, str]:
    """Return current date/time in ISO format and a human-friendly string.

    Args:
            tz: optional timezone (datetime.tzinfo). If omitted, uses system local time.

    Returns:
            dict with keys: 'iso', 'human', 'timestamp'
    """
    now = datetime.datetime.now(tz=tz)
    return {
        "iso": now.isoformat(),
        "human": now.strftime("%Y-%m-%d %H:%M:%S"),
        "timestamp": str(int(now.timestamp())),
    }
