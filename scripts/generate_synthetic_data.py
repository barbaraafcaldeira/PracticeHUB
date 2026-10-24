#!/usr/bin/env python3
"""Compatibility entry point for the validated v2 dataset rebuild."""

import runpy
from pathlib import Path

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).with_name("rebuild_dataset.py")), run_name="__main__")
