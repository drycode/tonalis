"""Make the release scripts importable the way the workflows invoke them."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
