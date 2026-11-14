#!/usr/bin/env python3
"""RETIRED (Nov 14, 2026) — do not use.

The old sticky section nav (Top Stories / Latest / Learn / Listen) was
replaced sitewide by the professional two-part header installed by
tools/set-topnav.py (mark + DTBRIEF wordmark, section links, Listen
dropdown, header search, Subscribe pill, mobile hamburger).

To add or refresh the header on any page, run:

    python3 tools/set-topnav.py

This file is kept only as a pointer so nothing re-adds the old nav.
"""
import sys


def main():
    print("add-sticky-nav.py is retired — use tools/set-topnav.py instead.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
