#!/usr/bin/env python3
"""Russian-language entry point for the shared installer API.

All installation behavior remains implemented in :mod:`install`; this file
only selects the Russian user interface for convenient direct invocation.
"""
from __future__ import annotations

import sys

from install import main


if __name__ == "__main__":
    # argparse uses the last occurrence, so the dedicated entry point always
    # remains Russian even when a copied command includes another --lang flag.
    sys.argv.extend(("--lang", "ru"))
    main()
