"""
Command Line Interface for Web Snapshot Tool.

コマンドライン引数のパースとバリデーションを担当します。
"""

import argparse
import sys
from typing import Optional

from playwright.async_api import Error as PlaywrightError

from websnapshot.screenshot import take_screenshot
from websnapshot.utils import is_valid_url, normalize_url


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


def parse_arguments() -> argparse.Namespace:
    """
    コマンドライン引数を解析する。

    Returns:
        argparse.Namespace: 解析された引数
    """
    parser = argparse.ArgumentParser(
        description='Webページのスクリーンショットを取得するCLIツール（OCR機能付き）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
使用例:
  python -m websnapshot https://example.com
  python -m websnapshot example.com --width 1280 --height 720
  python -m websnapshot https://example.com --output my-screenshot.png
  python -m websnapshot https://example.com --viewport --wait 2000
  python -m websnapshot https://example.com --ocr
  python -m websnapshot https://example.com --ocr --ocr-format json
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

    # OCR関連オプション
    parser.add_argument(
        '--ocr',
        action='store_true',
        help='OCR機能を有効化'
    )

    parser.add_argument(
        '--ocr-lang',
        type=str,
        default='ja+en',
        metavar='LANGUAGES',
        help='OCR対象言語（複数可: +区切り、デフォルト: ja+en）'
    )

    parser.add_argument(
        '--ocr-output',
        type=str,
        default=None,
        metavar='FILE',
        help='OCR結果出力ファイルパス（デフォルト: ocr_report-{timestamp}.md）'
    )

    parser.add_argument(
        '--ocr-format',
        type=str,
        choices=['text', 'json', 'markdown'],
        default='markdown',
        metavar='FORMAT',
        help='出力フォーマット（text/json/markdown、デフォルト: markdown）'
    )

    parser.add_argument(
        '--ocr-api-key',
        type=str,
        default=None,
        metavar='KEY',
        help='GLM APIキー（省略時は環境変数GLM_API_KEYまたは.envファイル）'
    )

    parser.add_argument(
        '--ocr-model',
        type=str,
        default='glm-4v',
        metavar='MODEL',
        help='使用するGLMモデル（デフォルト: glm-4v）'
    )

    return parser.parse_args()


async def run_screenshot(args: argparse.Namespace) -> tuple[int, Optional[str], Optional[str]]:
    """
    スクリーンショット取得を実行する。

    この関数は単体テストでのモックを容易にするために分離されている。

    Args:
        args: パースされたコマンドライン引数

    Returns:
        tuple[int, Optional[str], Optional[str]]: (終了コード, 保存されたファイルパス, OCR結果ファイルパス)
        エラー時は (error_code, error_message, None) を返す
    """
    exit_code, error_msg = validate_options(args)
    if exit_code != 0:
        return exit_code, error_msg, None

    if not is_valid_url(args.url):
        return 1, f"エラー: 無効なURL '{args.url}'\n有効なURLを指定してください（例: https://example.com）", None

    normalized_url = normalize_url(args.url)

    try:
        saved_path, ocr_path = await take_screenshot(
            normalized_url,
            output_path=args.output,
            width=args.width,
            height=args.height,
            wait=args.wait,
            full_page=not args.viewport,
            ocr=args.ocr,
            ocr_lang=args.ocr_lang,
            ocr_output=args.ocr_output,
            ocr_format=args.ocr_format,
            ocr_api_key=args.ocr_api_key,
            ocr_model=args.ocr_model
        )
        return 0, saved_path, ocr_path

    except ValueError as e:
        return 1, f"設定エラー: {e}", None

    except PlaywrightError as e:
        return 1, f"エラー: ページの読み込みに失敗しました: {e}", None

    except IOError as e:
        return 1, f"エラー: ファイルの保存に失敗しました: {e}", None

    except Exception as e:
        return 1, f"エラー: 予期しないエラーが発生しました: {e}", None


async def main() -> int:
    """
    メイン関数。

    Returns:
        int: 終了コード（0: 成功, 1: エラー）
    """
    args = parse_arguments()

    print(f"スクリーンショットを取得中: {args.url}")

    exit_code, screenshot_path, ocr_path = await run_screenshot(args)

    if exit_code == 0:
        print(f"スクリーンショットを保存しました: {screenshot_path}")
        if args.ocr and ocr_path:
            print(f"OCR結果を保存しました: {ocr_path}")
    else:
        print(screenshot_path)

    return exit_code


def cli():
    """コンソールスクリプト用エントリーポイント（同期ラッパー）。"""
    import asyncio
    sys.exit(asyncio.run(main()))
