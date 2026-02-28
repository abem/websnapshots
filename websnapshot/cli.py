"""
Command Line Interface for Web Snapshot Tool.

コマンドライン引数のパースとバリデーションを担当します。
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from playwright.async_api import Error as PlaywrightError

from websnapshot.screenshot import take_screenshot
from websnapshot.utils import is_valid_url, normalize_url, generate_filename


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
  python -m websnapshot https://example.com --output-dir ./screenshots
  python -m websnapshot https://example.com --viewport --wait 2000
  python -m websnapshot https://example.com --ocr
  python -m websnapshot --batch urls.txt
        '''
    )

    parser.add_argument(
        'url',
        nargs='?',
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
        '--output-dir',
        type=str,
        default=None,
        metavar='DIR',
        help='出力ディレクトリ（指定しない場合はカレントディレクトリ）'
    )

    parser.add_argument(
        '--batch',
        type=str,
        default=None,
        metavar='FILE',
        help='URLリストファイルから一括処理'
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


def validate_args(args: argparse.Namespace) -> tuple[int, Optional[str]]:
    """
    コマンドライン引数をバリデーションする。

    Args:
        args: パースされたコマンドライン引数

    Returns:
        tuple[int, Optional[str]]: (終了コード, エラーメッセージ)
    """
    if not args.url and not args.batch:
        return 1, "エラー: URLまたは--batchオプションを指定してください"
    return 0, None


def resolve_output_path(args: argparse.Namespace) -> str:
    """
    出力パスを解決する。

    Args:
        args: パースされたコマンドライン引数

    Returns:
        str: 出力ファイルパス
    """
    if args.output:
        filename = args.output
    else:
        filename = generate_filename()

    if args.output_dir:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        return str(output_dir / filename)

    return filename


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
    output_path = resolve_output_path(args)

    try:
        saved_path, ocr_path = await take_screenshot(
            normalized_url,
            output_path=output_path,
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


async def run_batch(args: argparse.Namespace) -> int:
    """
    バッチ処理を実行する。

    Args:
        args: パースされたコマンドライン引数

    Returns:
        int: 終了コード
    """
    batch_file = Path(args.batch)
    if not batch_file.exists():
        print(f"エラー: バッチファイルが見つかりません: {args.batch}")
        return 1

    urls = [line.strip() for line in batch_file.read_text().splitlines() if line.strip()]
    if not urls:
        print("エラー: バッチファイルにURLが含まれていません")
        return 1

    print(f"バッチ処理開始: {len(urls)}件のURL")

    success_count = 0
    error_count = 0

    for i, url in enumerate(urls, 1):
        print(f"\n[{i}/{len(urls)}] {url}")
        args.url = url
        args.output = None  # 自動生成

        exit_code, result, _ = await run_screenshot(args)
        if exit_code == 0:
            print(f"  ✅ 保存しました: {result}")
            success_count += 1
        else:
            print(f"  ❌ {result}")
            error_count += 1

    print(f"\nバッチ処理完了: 成功 {success_count}件, エラー {error_count}件")
    return 0 if error_count == 0 else 1


async def main() -> int:
    """
    メイン関数。

    Returns:
        int: 終了コード（0: 成功, 1: エラー）
    """
    args = parse_arguments()

    # 引数バリデーション
    exit_code, error_msg = validate_args(args)
    if exit_code != 0:
        print(error_msg)
        return exit_code

    # バッチ処理
    if args.batch:
        return await run_batch(args)

    # 単一URL処理
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
