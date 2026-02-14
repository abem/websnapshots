"""
Web Snapshot Tool

Webページのスクリーンショットを取得するCLIツール。
モジュール版のエントリーポイント。
"""

from websnapshot.screenshot import take_screenshot
from websnapshot.ocr import perform_ocr, generate_ocr_report
from websnapshot.utils import is_valid_url, normalize_url, generate_filename

__version__ = "2.0.0"
__all__ = [
    "take_screenshot",
    "perform_ocr",
    "generate_ocr_report",
    "is_valid_url",
    "normalize_url",
    "generate_filename",
]
