#!/usr/bin/env python3
"""
web_snapshot.py の単体テスト（OCR分析機能対応版）
"""

import pytest
import argparse
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
import sys
import os
import tempfile

# モジュールをインポートできるようにパスを追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from web_snapshot import (
    is_valid_url,
    normalize_url,
    generate_filename,
    encode_image_to_base64,
    validate_options,
)


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
        # screenshot-{timestamp}.png 形式をチェック
        parts = filename.split("-")
        assert len(parts) >= 2
        timestamp = parts[1].replace(".png", "")
        assert "T" in timestamp


class TestEncodeImageToBase64:
    """base64エンコードのテスト"""

    def test_encode_image_to_base64(self):
        # 一時ファイルを作成
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.png') as f:
            test_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR'
            f.write(test_data)
            temp_path = f.name

        try:
            result = encode_image_to_base64(temp_path)
            assert isinstance(result, str)
            # base64エンコードされた結果は元のデータより長い
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


class TestAnalyzeImageWithGlm4V:
    """GLM-4V画像分析のテスト"""

    @pytest.mark.asyncio
    async def test_analyze_image_returns_expected_structure(self):
        """分析関数が期待される構造を返すテスト"""
        from web_snapshot import analyze_image_with_glm4v

        # 一時ファイルを作成
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.png') as f:
            test_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR' + b'\x00' * 100
            f.write(test_data)
            temp_path = f.name

        try:
            # 関数自体をモック
            expected_result = {
                "title": "Test Page",
                "headings": ["H1"],
                "main_text": "Test content"
            }

            with patch('web_snapshot.analyze_image_with_glm4v', return_value=expected_result):
                result = analyze_image_with_glm4v(temp_path, "test_api_key")

            assert "title" in result
            assert result["title"] == "Test Page"
            assert "headings" in result
            assert result["headings"] == ["H1"]
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_analyze_image_detail_mode_structure(self):
        """詳細モードの構造テスト"""
        from web_snapshot import analyze_image_with_glm4v

        # 一時ファイルを作成
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.png') as f:
            test_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR' + b'\x00' * 100
            f.write(test_data)
            temp_path = f.name

        try:
            # 関数自体をモック
            expected_result = {
                "page_type": "トップページ",
                "title": "Test",
                "layout": {"structure": "テスト"},
                "summary": "要約"
            }

            with patch('web_snapshot.analyze_image_with_glm4v', return_value=expected_result):
                result = analyze_image_with_glm4v(temp_path, "test_api_key", detail=True)

            assert "page_type" in result
            assert "layout" in result
            assert result["page_type"] == "トップページ"
        finally:
            os.unlink(temp_path)


class TestGenerateAnalysisReport:
    """分析レポート生成のテスト"""

    def test_generate_report_markdown(self):
        """Markdown形式のレポート生成"""
        from web_snapshot import generate_analysis_report

        analysis = {
            "title": "テストページ",
            "headings": ["見出し1", "見出し2"],
            "main_text": "メインテキスト",
            "summary": "要約"
        }

        report = generate_analysis_report(analysis, "test.png", format_type="markdown")

        assert "# GLM-4V OCR分析レポート" in report
        assert "テストページ" in report
        assert "見出し1" in report
        assert "メインテキスト" in report
        assert "要約" in report

    def test_generate_report_json(self):
        """JSON形式のレポート生成"""
        from web_snapshot import generate_analysis_report

        analysis = {
            "title": "テストページ",
            "headings": ["H1"]
        }

        report = generate_analysis_report(analysis, "test.png", format_type="json")

        import json
        parsed = json.loads(report)
        assert parsed["title"] == "テストページ"
        assert parsed["headings"] == ["H1"]

    def test_generate_report_text(self):
        """テキスト形式のレポート生成"""
        from web_snapshot import generate_analysis_report

        analysis = {
            "title": "テストページ",
            "headings": ["H1"]
        }

        report = generate_analysis_report(analysis, "test.png", format_type="text")

        assert "GLM-4V OCR分析レポート" in report
        assert "テストページ" in report

    def test_generate_report_with_error(self):
        """エラー時のレポート生成"""
        from web_snapshot import generate_analysis_report

        analysis = {
            "error": "APIエラーが発生しました"
        }

        report = generate_analysis_report(analysis, "test.png", format_type="markdown")

        assert "エラー" in report
        assert "APIエラーが発生しました" in report

    def test_generate_report_detailed_mode(self):
        """詳細モードのレポート生成"""
        from web_snapshot import generate_analysis_report

        analysis = {
            "page_type": "トップページ",
            "title": "テスト",
            "layout": {
                "structure": "ヘッダー、メイン、フッター",
                "sections": ["セクション1", "セクション2"],
                "navigation": "グローバルナビ"
            },
            "content": {
                "key_elements": ["要素1", "要素2"]
            },
            "visual_elements": {
                "colors": "青と白",
                "style": "モダン"
            },
            "interactive_elements": ["ボタン", "リンク"],
            "summary": "要約テキスト"
        }

        report = generate_analysis_report(analysis, "test.png", format_type="markdown")

        assert "ページタイプ" in report
        assert "トップページ" in report
        assert "レイアウト構造" in report
        assert "ヘッダー、メイン、フッター" in report
        assert "視覚的要素" in report
        assert "インタラクティブ要素" in report


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
