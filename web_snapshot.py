#!/usr/bin/env python3
"""
Web Snapshot Tool - エントリーポイント

従来通り `python web_snapshot.py <url>` で実行するためのラッパー。
"""

from websnapshot.cli import cli

if __name__ == '__main__':
    cli()
