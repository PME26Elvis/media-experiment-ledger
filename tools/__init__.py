"""Repository tool modules.

Most command-line entrypoints are executed as ``python tools/name.py`` and use
sibling imports.  Adding the tools directory to ``sys.path`` also lets the same
modules be imported as ``tools.name`` by unittest without maintaining two sets
of import statements.
"""
from __future__ import annotations

import sys
from pathlib import Path

TOOLS_ROOT = str(Path(__file__).resolve().parent)
if TOOLS_ROOT not in sys.path:
    sys.path.insert(0, TOOLS_ROOT)
