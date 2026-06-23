#!/usr/bin/env python3
"""Start Wellnest local server (dashboard + Oura OAuth)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.local_server import main

if __name__ == "__main__":
    main()
