#!/usr/bin/env python3
"""Runs the launcher for a package installed by Casca."""

import sys

from casca.package_launcher import main

if __name__ == "__main__":
    sys.exit(main())
