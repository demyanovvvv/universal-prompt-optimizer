#!/usr/bin/env python3
"""Complete uninstall using the shared installer CLI and transactions."""
import sys

from install import main


if __name__ == "__main__":
    sys.argv.append("--uninstall")
    main()
