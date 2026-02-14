"""
Web Snapshot Tool - Main Entry Point

Webページのスクリーンショットを取得するCLIツール。
モジュール版のメインエントリーポイント。
"""

import sys
from websnapshot.cli import cli

if __name__ == '__main__':
    cli()
