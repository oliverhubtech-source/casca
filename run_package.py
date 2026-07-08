#!/usr/bin/env python3
"""Executa o launcher de um pacote instalado pelo Casca."""

import sys

from casca.package_launcher import main

if __name__ == "__main__":
    sys.exit(main())
