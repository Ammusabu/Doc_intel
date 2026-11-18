"""Path setup + per-loop engine cleanup."""
import asyncio
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


@pytest.fixture(autouse=True)
async def _dispose_engine_per_test():
    """Dispose the current event loop's engine after each test to prevent leaks."""
    yield
    try:
        from app.db import session as dbmod
        loop = asyncio.get_running_loop()
        pair = dbmod._cache.pop(loop, None)
        if pair is not None:
            _, factory = pair
            # Dispose engine by borrowing the bind
            eng = factory.kw.get("bind") if hasattr(factory, "kw") else None
            if eng is not None:
                await eng.dispose()
    except Exception:
        pass
