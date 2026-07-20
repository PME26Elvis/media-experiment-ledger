"""Compatibility facade for tools.release_policy.

Some legacy tests and ad-hoc callers load tools/analyze_releases.py through an
importlib file specification without adding tools/ to sys.path. Production CLI
execution still imports tools/release_policy.py directly.
"""
from tools.release_policy import *  # noqa: F401,F403
