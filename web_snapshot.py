#!/usr/bin/env python3
"""
Web Snapshot Tool

Webページのスクリーンショットを取得するCLIツール。
"""

import argparse
import sys
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from typing import Optional

try:
    from playwright.async_api import async_playwright, Error as PlaywrightError
except ImportError:
    print("エラー: Playwright がインストールされていません。")
    print("以下のコマンドでインストールしてください:")
    print("  pip install playwright")
    print("  playwright install chromium")
    sys.exit(1)


def is_valid_url(url: str) -> bool:
    """
    URLが有効かどうかをバリデーションする。
    ドメイン名、IPアドレス、localhost、ポート番号付きURLに対応。

    Args:
        url: バリデーションするURL文字列

    Returns:
        bool: URLが有効な場合はTrue
    """
    if not url or len(url) < 3:
        return False

    # http:// または https:// が省略されている場合は追加
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    try:
        result = urlparse(url)
        # schemeとnetlocが存在すれば有効と判定
        # これによりドメイン名、IPアドレス、localhost、ポート番号付きURLすべてに対応
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def normalize_url(url: str) -> str:
    """
    URLを正規化する（プロトコルが省略されている場合は補完）。

    Args:
        url: 正規化するURL文字列

    Returns:
        str: 正規化されたURL
    """
    if not url.startswith(('http://', 'https://')):
        return 'https://' + url
    return url


def generate_filename() -> str:
    """
    タイムスタンプ付きのファイル名を生成する。

    Returns:
        str: screenshot-{timestamp}.png 形式のファイル名
    """
    timestamp = datetime.now().strftime('%Y%m%dT%H%M%S')
    return f'screenshot-{timestamp}.png'


def validate_options(args: argparse.Namespace) -> tuple[int, Optional[str]]:
    """
    コマンドラインオプションをバリデーションする。

    Args:
        args: パースされたコマンドライン引数

    Returns:
        tuple[int, Optional[str]]: (終了コード, エラーメッセージ)
        エラーがない場合は (0, None) を返す
    """
    if args.width <= 0:
        return 1, "エラー: --width は正の値である必要があります"
    if args.height <= 0:
        return 1, "エラー: --height は正の値である必要があります"
    if args.wait is not None and args.wait < 0:
        return 1, "エラー: --wait は0以上の値である必要があります"

    return 0, None


async def take_screenshot(
    url: str,
    output_path: Optional[str] = None,
    width: int = 1920,
    height: int = 1080,
    wait: Optional[int] = None,
    full_page: bool = True
) -> str:
    """
    指定されたURLのスクリーンショットを取得する。

    Args:
        url: スクリーンショットを取得するURL
        output_path: 出力ファイルパス（省略時は自動生成）
        width: ビューポートの幅（ピクセル）
        height: ビューポートの高さ（ピクセル）
        wait: ページ読み込み後の追加待機時間（ミリ秒）
        full_page: フルページスクリーンショットを取得するかどうか

    Returns:
        str: 保存されたファイルのパス

    Raises:
        PlaywrightError: ブラウザ操作エラー
        IOError: ファイル保存エラー
    """
    if output_path is None:
        output_path = generate_filename()

    async with async_playwright() as p:
        # ブラウザを起動（ヘッドレスモード）
        browser = await p.chromium.launch(headless=True)

        try:
            # ページを作成し、ビューポートサイズを設定
            page = await browser.new_page(viewport={'width': width, 'height': height})

            # ページを読み込み
            await page.goto(url, wait_until='networkidle', timeout=30000)

            # 追加の待機時間が指定されている場合は待機
            if wait is not None and wait > 0:
                await page.wait_for_timeout(wait)

            # スクリーンショットを保存
            await page.screenshot(path=output_path, full_page=full_page)

            return output_path

        finally:
            await browser.close()


def parse_arguments() -> argparse.Namespace:
    """
    コマンドライン引数を解析する。

    Returns:
        argparse.Namespace: 解析された引数
    """
    parser = argparse.ArgumentParser(
        description='Webページのスクリーンショットを取得するCLIツール',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
使用例:
  python web_snapshot.py https://example.com
  python web_snapshot.py example.com --width 1280 --height 720
  python web_snapshot.py https://example.com --output my-screenshot.png
  python web_snapshot.py https://example.com --viewport --wait 2000
        '''
    )

    parser.add_argument(
        'url',
        help='スクリーンショットを取得するWebページのURL'
    )

    parser.add_argument(
        '--width',
        type=int,
        default=1920,
        metavar='PIXELS',
        help='ウィンドウの幅（デフォルト: 1920）'
    )

    parser.add_argument(
        '--height',
        type=int,
        default=1080,
        metavar='PIXELS',
        help='ウィンドウの高さ（デフォルト: 1080）'
    )

    parser.add_argument(
        '--output', '-o',
        type=str,
        default=None,
        metavar='FILE',
        help='出力ファイル名（デフォルト: screenshot-{timestamp}.png）'
    )

    parser.add_argument(
        '--wait',
        type=int,
        default=None,
        metavar='MILLISECONDS',
        help='ページ読み込み後の追加待機時間（ミリ秒）'
    )

    parser.add_argument(
        '--viewport',
        action='store_true',
        help='ビューポートのみのスクリーンショットを取得する（デフォルトはフルページ）'
    )

    return parser.parse_args()


async def run_screenshot(args: argparse.Namespace) -> tuple[int, Optional[str]]:
    """
    スクリーンショット取得を実行する。

    この関数は単体テストでのモックを容易にするために分離されている。

    Args:
        args: パースされたコマンドライン引数

    Returns:
        tuple[int, Optional[str]]: (終了コード, 保存されたファイルパス)
        エラー時は (1, None) を返す
    """
    # オプションのバリデーション
    exit_code, error_msg = validate_options(args)
    if exit_code != 0:
        return exit_code, error_msg

    # URLのバリデーション
    if not is_valid_url(args.url):
        return 1, f"エラー: 無効なURL '{args.url}'"

    # URLを正規化
    normalized_url = normalize_url(args.url)

    try:
        saved_path = await take_screenshot(
            normalized_url,
            output_path=args.output,
            width=args.width,
            height=args.height,
            wait=args.wait,
            full_page=not args.viewport  # --viewport指定時のみビューポートのみ
        )
        return 0, saved_path

    except PlaywrightError as e:
        return 1, f"エラー: ページの読み込みに失敗しました: {e}"

    except IOError as e:
        return 1, f"エラー: ファイルの保存に失敗しました: {e}"

    except Exception as e:
        return 1, f"エラー: 予期しないエラーが発生しました: {e}"


async def main() -> int:
    """
    メイン関数。

    Returns:
        int: 終了コード（0: 成功, 1: エラー）
    """
    args = parse_arguments()

    # オプションのバリデーション
    exit_code, error_msg = validate_options(args)
    if exit_code != 0:
        print(error_msg)
        return exit_code

    # URLのバリデーション
    if not is_valid_url(args.url):
        print(f"エラー: 無効なURL '{args.url}'")
        print("有効なURLを指定してください（例: https://example.com）")
        return 1

    # URLを正規化
    normalized_url = normalize_url(args.url)

    print(f"スクリーンショットを取得中: {normalized_url}")

    exit_code, result = await run_screenshot(args)

    if exit_code == 0:
        print(f"スクリーンショットを保存しました: {result}")
    else:
        print(result)

    return exit_code


if __name__ == '__main__':
    import asyncio
    sys.exit(asyncio.run(main()))
