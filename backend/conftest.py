"""Force `backend/` onto sys.path so `import app` works regardless of cwd."""
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
