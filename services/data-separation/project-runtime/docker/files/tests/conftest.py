import sys
from pathlib import Path

# Make `app` importable when running pytest from docker/files.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
