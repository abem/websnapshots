#!/usr/bin/env python3
"""
CLI tests for Web Snapshot Tool.
"""

import argparse
import sys
import tempfile
from pathlib import Path

# テスト対象をインポート
from websnapshot.cli import validate_args, resolve_output_path


def test_validate_args_no_url():
    """URLも--batchも指定されていない場合のテスト"""
    args = argparse.Namespace(url=None, batch=None, width=1920, height=1080, wait=None)
    exit_code, error_msg = validate_args(args)
    assert exit_code == 1
    assert "URLまたは--batch" in error_msg
    print("✅ test_validate_args_no_url")


def test_validate_args_with_url():
    """URLが指定されている場合のテスト"""
    args = argparse.Namespace(url="https://example.com", batch=None, width=1920, height=1080, wait=None)
    exit_code, error_msg = validate_args(args)
    assert exit_code == 0
    assert error_msg is None
    print("✅ test_validate_args_with_url")


def test_validate_args_with_batch():
    """--batchが指定されている場合のテスト"""
    args = argparse.Namespace(url=None, batch="urls.txt", width=1920, height=1080, wait=None)
    exit_code, error_msg = validate_args(args)
    assert exit_code == 0
    assert error_msg is None
    print("✅ test_validate_args_with_batch")


def test_validate_args_invalid_width():
    """幅が無効な場合のテスト"""
    args = argparse.Namespace(url="https://example.com", batch=None, width=-100, height=1080, wait=None)
    exit_code, error_msg = validate_args(args)
    assert exit_code == 1
    assert "width" in error_msg
    print("✅ test_validate_args_invalid_width")


def test_validate_args_invalid_height():
    """高さが無効な場合のテスト"""
    args = argparse.Namespace(url="https://example.com", batch=None, width=1920, height=0, wait=None)
    exit_code, error_msg = validate_args(args)
    assert exit_code == 1
    assert "height" in error_msg
    print("✅ test_validate_args_invalid_height")


def test_validate_args_negative_wait():
    """待機時間が負の場合のテスト"""
    args = argparse.Namespace(url="https://example.com", batch=None, width=1920, height=1080, wait=-1000)
    exit_code, error_msg = validate_args(args)
    assert exit_code == 1
    assert "wait" in error_msg
    print("✅ test_validate_args_negative_wait")


def test_resolve_output_path_default():
    """デフォルトの出力パステスト"""
    args = argparse.Namespace(output=None, output_dir=None)
    path = resolve_output_path(args)
    assert "screenshot-" in path
    assert path.endswith(".png")
    print("✅ test_resolve_output_path_default")


def test_resolve_output_path_custom_filename():
    """カスタムファイル名のテスト"""
    args = argparse.Namespace(output="custom.png", output_dir=None)
    path = resolve_output_path(args)
    assert path == "custom.png"
    print("✅ test_resolve_output_path_custom_filename")


def test_resolve_output_path_with_output_dir():
    """出力ディレクトリ指定のテスト"""
    with tempfile.TemporaryDirectory() as tmpdir:
        args = argparse.Namespace(output="test.png", output_dir=tmpdir)
        path = resolve_output_path(args)
        assert path == str(Path(tmpdir) / "test.png")
        assert Path(tmpdir).exists()
    print("✅ test_resolve_output_path_with_output_dir")


def run_all_tests():
    """すべてのテストを実行"""
    print("=== CLI Tests ===\n")

    tests = [
        test_validate_args_no_url,
        test_validate_args_with_url,
        test_validate_args_with_batch,
        test_validate_args_invalid_width,
        test_validate_args_invalid_height,
        test_validate_args_negative_wait,
        test_resolve_output_path_default,
        test_resolve_output_path_custom_filename,
        test_resolve_output_path_with_output_dir,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"❌ {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ {test.__name__}: 予期しないエラー - {e}")
            failed += 1

    print(f"\n=== Results ===")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
