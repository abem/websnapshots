#!/usr/bin/env python3
"""
websnapshotパッケージの単体テスト
"""

import pytest
import argparse
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
import sys
import os
import tempfile

# モジュールをインポートできるようにパスを追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from websnapshot.utils import (
    is_valid_url,
    normalize_url,
    generate_filename,
    encode_image_to_base64,
)
from websnapshot.cli import validate_options


class TestUrlValidation:
    """URLバリデーションのテスト"""

    def test_valid_url_with_https(self):
        assert is_valid_url("https://example.com") == True

    def test_valid_url_with_http(self):
        assert is_valid_url("http://example.com") == True

    def test_valid_url_without_protocol(self):
        assert is_valid_url("example.com") == True

    def test_valid_url_with_ip(self):
        assert is_valid_url("192.168.1.1") == True

    def test_valid_url_with_localhost(self):
        assert is_valid_url("localhost") == True
        assert is_valid_url("localhost:8080") == True

    def test_valid_url_with_port(self):
        assert is_valid_url("example.com:8080") == True
        assert is_valid_url("https://example.com:8443") == True

    def test_invalid_url_empty(self):
        assert is_valid_url("") == False

    def test_invalid_url_too_short(self):
        assert is_valid_url("ab") == False

    def test_invalid_url_no_valid_chars(self):
        assert is_valid_url("://") == False

    def test_invalid_url_only_spaces(self):
        assert is_valid_url("   ") == False


class TestUrlNormalization:
    """URL正規化のテスト"""

    def test_normalize_url_with_https(self):
        assert normalize_url("https://example.com") == "https://example.com"

    def test_normalize_url_with_http(self):
        assert normalize_url("http://example.com") == "http://example.com"

    def test_normalize_url_without_protocol(self):
        assert normalize_url("example.com") == "https://example.com"

    def test_normalize_url_with_subdomain(self):
        assert normalize_url("sub.example.com") == "https://sub.example.com"


class TestFilenameGeneration:
    """ファイル名生成のテスト"""

    def test_generate_filename_default(self):
        filename = generate_filename()
        assert filename.startswith("screenshot-")
        assert filename.endswith(".png")

    def test_generate_filename_custom_prefix(self):
        filename = generate_filename(prefix="analysis")
        assert filename.startswith("analysis-")
        assert filename.endswith(".png")

    def test_generate_filename_custom_ext(self):
        filename = generate_filename(ext="md")
        assert filename.startswith("screenshot-")
        assert filename.endswith(".md")

    def test_generate_filename_timestamp_format(self):
        filename = generate_filename()
        parts = filename.split("-")
        assert len(parts) >= 2
        timestamp = parts[1].replace(".png", "")
        assert "T" in timestamp


class TestEncodeImageToBase64:
    """base64エンコードのテスト"""

    def test_encode_image_to_base64(self):
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.png') as f:
            test_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR'
            f.write(test_data)
            temp_path = f.name

        try:
            result = encode_image_to_base64(temp_path)
            assert isinstance(result, str)
            assert len(result) > 0
        finally:
            os.unlink(temp_path)


class TestValidateOptions:
    """オプションバリデーションのテスト"""

    def test_validate_options_valid(self):
        args = argparse.Namespace(
            width=1920,
            height=1080,
            wait=1000,
            url="https://example.com",
            output=None,
            viewport=False
        )
        exit_code, error_msg = validate_options(args)
        assert exit_code == 0
        assert error_msg is None

    def test_validate_options_invalid_width_zero(self):
        args = argparse.Namespace(
            width=0,
            height=1080,
            wait=1000,
            url="https://example.com",
            output=None,
            viewport=False
        )
        exit_code, error_msg = validate_options(args)
        assert exit_code == 1
        assert "width" in error_msg
        assert "正の値" in error_msg

    def test_validate_options_invalid_width_negative(self):
        args = argparse.Namespace(
            width=-100,
            height=1080,
            wait=1000,
            url="https://example.com",
            output=None,
            viewport=False
        )
        exit_code, error_msg = validate_options(args)
        assert exit_code == 1
        assert "width" in error_msg

    def test_validate_options_invalid_height_zero(self):
        args = argparse.Namespace(
            width=1920,
            height=0,
            wait=1000,
            url="https://example.com",
            output=None,
            viewport=False
        )
        exit_code, error_msg = validate_options(args)
        assert exit_code == 1
        assert "height" in error_msg

    def test_validate_options_invalid_wait_negative(self):
        args = argparse.Namespace(
            width=1920,
            height=1080,
            wait=-100,
            url="https://example.com",
            output=None,
            viewport=False
        )
        exit_code, error_msg = validate_options(args)
        assert exit_code == 1
        assert "wait" in error_msg
        assert "0以上" in error_msg

    def test_validate_options_wait_zero_valid(self):
        args = argparse.Namespace(
            width=1920,
            height=1080,
            wait=0,
            url="https://example.com",
            output=None,
            viewport=False
        )
        exit_code, error_msg = validate_options(args)
        assert exit_code == 0
        assert error_msg is None

    def test_validate_options_wait_none_valid(self):
        args = argparse.Namespace(
            width=1920,
            height=1080,
            wait=None,
            url="https://example.com",
            output=None,
            viewport=False
        )
        exit_code, error_msg = validate_options(args)
        assert exit_code == 0
        assert error_msg is None


class TestOcrFunctions:
    """OCR機能のテスト"""

    def test_generate_ocr_report_markdown(self):
        """Markdown形式のOCRレポート生成"""
        from websnapshot.ocr import generate_ocr_report

        ocr_result = {
            "page_title": "テストページ",
            "text_blocks": [
                {"type": "heading", "text": "見出し1"},
                {"type": "paragraph", "text": "本文"}
            ],
            "links": [{"text": "リンク", "href": "https://example.com"}]
        }

        report = generate_ocr_report(ocr_result, "test.png", "https://example.com", format_type="markdown")

        assert "# OCRレポート" in report
        assert "テストページ" in report
        assert "見出し1" in report
        assert "本文" in report

    def test_generate_ocr_report_json(self):
        """JSON形式のOCRレポート生成"""
        from websnapshot.ocr import generate_ocr_report

        ocr_result = {
            "page_title": "テストページ",
            "text_blocks": [{"type": "heading", "text": "見出し1"}]
        }

        report = generate_ocr_report(ocr_result, "test.png", "https://example.com", format_type="json")

        import json
        parsed = json.loads(report)
        assert parsed["page_title"] == "テストページ"
        assert parsed["text_blocks"][0]["text"] == "見出し1"

    def test_generate_ocr_report_with_error(self):
        """エラー時のOCRレポート生成"""
        from websnapshot.ocr import generate_ocr_report

        ocr_result = {
            "error": "APIエラーが発生しました"
        }

        report = generate_ocr_report(ocr_result, "test.png", "https://example.com", format_type="markdown")

        assert "エラー" in report
        assert "APIエラーが発生しました" in report


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
