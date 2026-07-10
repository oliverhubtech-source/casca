#!/usr/bin/env python3
"""Runs a web app's own window as created by Casca (WebKitGTK engine)."""

import sys

from casca.webview_app import main

if __name__ == "__main__":
    sys.exit(main())
