import sys
from pathlib import Path

# Make `app` importable whatever directory pytest is invoked from.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
