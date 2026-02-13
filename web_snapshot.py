#!/usr/bin/env python3
"""
Web Snapshot Tool

Webページのスクリーンショットを取得するCLIツール。
"""

import argparse
import asyncio
import base64
import json
import os
import sys
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from typing import Optional, Dict, Any

# .envファイルから環境変数を読み込む
try:
    from dotenv import load_dotenv

    # .envファイルを複数の場所から検索
    # 優先順位: カレントディレクトリ > スクリプトディレクトリ > ホームディレクトリ
    script_dir = Path(__file__).parent  # web_snapshot.pyのあるディレクトリ
    home_dir = Path.home()

    env_paths = [
        Path('.env'),                              # カレントディレクトリ
        script_dir / '.env',                       # スクリプトのあるディレクトリ
        home_dir / '.websnapshots' / '.env',      # ~/.websnapshots/.env
        home_dir / '.env',                         # ~/.env
    ]

    # 見つかった最初の.envファイルを読み込む
    for env_path in env_paths:
        if env_path.exists():
            load_dotenv(env_path, override=True)  # override=Trueで確実に上書き
            break
except ImportError:
    pass  # dotenvがない場合は環境変数を直接使用

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


def generate_filename(prefix: str = 'screenshot', ext: str = 'png') -> str:
    """
    タイムスタンプ付きのファイル名を生成する（プレフィックス指定可能）。

    Args:
        prefix: ファイル名のプレフィックス
        ext: 拡張子

    Returns:
        str: {prefix}-{timestamp}.{ext} 形式のファイル名
    """
    timestamp = datetime.now().strftime('%Y%m%dT%H%M%S')
    return f'{prefix}-{timestamp}.{ext}'


def encode_image_to_base64(image_path: str) -> str:
    """
    画像をbase64エンコードする。

    Args:
        image_path: 画像ファイルのパス

    Returns:
        str: base64エンコードされた画像データ
    """
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')


OCR_PROMPT = """Extract all text from this image. Return JSON only. Format:
{
  "page_title": "string",
  "text_blocks": [{"type": "string", "text": "string"}],
  "links": ["string"],
  "buttons": ["string"]
}"""


def perform_ocr(
    image_path: str,
    api_key: str,
    languages: str = "ja+en",
    model: str = "glm-4v"
) -> Dict[str, Any]:
    """
    GLM-4V APIを使用して画像をOCR分析する。

    Args:
        image_path: 分析する画像のパス
        api_key: GLM APIキー
        languages: 対象言語（+区切り、例: "ja+en"）
        model: 使用するモデル（デフォルト: glm-4v）
               利用可能なモデル: glm-4v, glm-4v-flash, glm-4v-plus, glm-4.5v, glm-4

    Returns:
        dict: OCR分析結果
    """
    # 画像をbase64エンコード
    base64_img = encode_image_to_base64(image_path)

    # クライアントの初期化（新旧SDK両対応）
    try:
        from zai import ZhipuAiClient
        USE_NEW_SDK = True
    except ImportError:
        from zhipuai import ZhipuAI
        USE_NEW_SDK = False

    if USE_NEW_SDK:
        client = ZhipuAiClient(api_key=api_key)
    else:
        client = ZhipuAI(api_key=api_key)

    # 言語指定をプロンプトに追加
    prompt = OCR_PROMPT
    if languages:
        lang_prompt = f"\n\n対象言語: {languages}\n以上の言語を中心にテキストを抽出してください。"
        prompt = OCR_PROMPT + lang_prompt

    # フォールバックモデルのリスト
    fallback_models = [model]
    if model == "glm-4v" and "glm-4v-plus" not in fallback_models:
        fallback_models.extend(["glm-4v-plus", "glm-4.6v", "glm-4.5v"])

    last_error = None

    for try_model in fallback_models:
        try:
            print(f"GLM-4VでOCR分析中... (モデル: {try_model})")
            response = client.chat.completions.create(
                model=try_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}
                            }
                        ]
                    }
                ],
                temperature=0.3,
                max_tokens=2000
            )

            # レスポンスからJSONを抽出
            content = response.choices[0].message.content

            # ```jsonと```を削除（もしあれば）
            content = content.strip()
            if content.startswith('```json'):
                content = content[7:]
            if content.startswith('```'):
                content = content[3:]
            if content.endswith('```'):
                content = content[:-3]

            # JSONをパース
            result = json.loads(content.strip())
            result["_model_used"] = try_model  # 使用したモデルを記録
            return result

        except Exception as e:
            last_error = e
            error_msg = str(e)
            # エラーコード1211（モデルが存在しない）の場合は次のモデルを試す
            if '1211' in error_msg or '模型不存在' in error_msg:
                print(f"  モデル {try_model} は利用できません。次のモデルを試します...")
                continue
            # その他のエラー場合は即座にリターン
            break

    return {
        "error": f"すべてのモデルでエラーが発生しました: {last_error}",
        "raw_response": content if 'content' in locals() else None,
        "_models_tried": fallback_models
    }


def generate_ocr_report(
    ocr_result: Dict[str, Any],
    image_path: str,
    url: str,
    format_type: str = "markdown"
) -> str:
    """
    OCR結果からレポートを生成する。

    Args:
        ocr_result: GLM-4VのOCR分析結果
        image_path: 分析した画像のパス
        url: 元のURL
        format_type: 出力フォーマット（markdown, json, text）

    Returns:
        str: 生成されたレポート
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if format_type == "json":
        return json.dumps(ocr_result, indent=2, ensure_ascii=False)

    if format_type == "text":
        # プレインテキスト形式
        lines = [
            "=== OCR結果 ===",
            f"URL: {url}",
            ""
        ]

        if "error" in ocr_result:
            lines.extend([
                f"エラー: {ocr_result['error']}"
            ])
            return '\n'.join(lines)

        if ocr_result.get('page_title'):
            lines.extend([
                f"タイトル: {ocr_result['page_title']}",
                ""
            ])

        # 全テキスト
        if ocr_result.get('full_text'):
            lines.extend([
                "【全テキスト】",
                ocr_result['full_text'],
                ""
            ])

        # テキストブロック
        if ocr_result.get('text_blocks'):
            lines.extend([
                "【テキストブロック】",
                ""
            ])
            for i, block in enumerate(ocr_result['text_blocks'], 1):
                block_type = block.get('type', 'unknown')
                text = block.get('text', '')
                location = block.get('location', '')
                lines.append(f"{i}. [{block_type}] {text}")
                if location:
                    lines.append(f"   位置: {location}")
            lines.append("")

        # リンク
        if ocr_result.get('links'):
            lines.extend([
                "【リンク】",
                ""
            ])
            for i, link in enumerate(ocr_result['links'], 1):
                text = link.get('text', '')
                href = link.get('href', '')
                location = link.get('location', '')
                lines.append(f"{i}. {text} -> {href}")
                if location:
                    lines.append(f"   位置: {location}")
            lines.append("")

        # メタデータ
        if ocr_result.get('metadata'):
            lines.extend([
                "【メタデータ】",
                ""
            ])
            metadata = ocr_result['metadata']
            for key, value in metadata.items():
                lines.append(f"{key}: {value}")

        return '\n'.join(lines)

    # Markdown形式（デフォルト）
    lines = [
        "# OCRレポート",
        "",
        f"**URL**: {url}",
        f"**抽出日時**: {timestamp}",
        ""
    ]

    if "error" in ocr_result:
        lines.extend([
            "## エラー",
            "",
            f"分析中にエラーが発生しました: {ocr_result['error']}",
        ])
        if ocr_result.get("raw_response"):
            lines.extend([
                "",
                "### 生レスポンス",
                "",
                "```",
                ocr_result["raw_response"],
                "```"
            ])
        return '\n'.join(lines)

    # ページタイトル
    if ocr_result.get('page_title'):
        lines.extend([
            f"**タイトル**: {ocr_result['page_title']}",
            ""
        ])

    # 全テキスト
    if ocr_result.get('full_text'):
        lines.extend([
            "## 全テキスト",
            "",
            ocr_result['full_text'],
            ""
        ])

    # テキストブロック詳細
    if ocr_result.get('text_blocks'):
        lines.extend([
            "## テキストブロック詳細",
            ""
        ])
        for block in ocr_result['text_blocks']:
            block_type = block.get('type', 'unknown')
            lines.extend([
                f"### {block_type}",
                f"- **テキスト**: {block.get('text', '')}",
                f"- **位置**: {block.get('location', '')}",
                f"- **信頼度**: {block.get('confidence', '')}",
                ""
            ])

    # リンク
    if ocr_result.get('links'):
        lines.extend([
            "## リンク",
            "",
            "| テキスト | URL | 位置 |",
            "|---------|-----|------|",
        ])
        for link in ocr_result['links']:
            text = link.get('text', '')
            href = link.get('href', '')
            location = link.get('location', '')
            lines.append(f"| {text} | {href} | {location} |")
        lines.append("")

    # メタデータ
    if ocr_result.get('metadata'):
        lines.extend([
            "## メタデータ",
            "",
            "| 項目 | 値 |",
            "|------|-----|",
        ])
        metadata = ocr_result['metadata']
        for key, value in metadata.items():
            lines.append(f"| {key} | {value} |")

    return '\n'.join(lines)


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
    full_page: bool = True,
    ocr: bool = False,
    ocr_lang: str = "ja+en",
    ocr_output: Optional[str] = None,
    ocr_format: str = "markdown",
    ocr_api_key: Optional[str] = None,
    ocr_model: str = "glm-4v"
) -> tuple[str, Optional[str]]:
    """
    指定されたURLのスクリーンショットを取得する。
    OCRオプションが指定されている場合、OCR分析も実行する。

    Args:
        url: スクリーンショットを取得するURL
        output_path: 出力ファイルパス（省略時は自動生成）
        width: ビューポートの幅（ピクセル）
        height: ビューポートの高さ（ピクセル）
        wait: ページ読み込み後の追加待機時間（ミリ秒）
        full_page: フルページスクリーンショットを取得するかどうか
        ocr: OCR分析を実行するかどうか
        ocr_lang: OCR対象言語（+区切り）
        ocr_output: OCR結果の出力ファイルパス
        ocr_format: OCR結果の出力フォーマット
        ocr_api_key: GLM APIキー
        ocr_model: 使用するGLMモデル

    Returns:
        tuple[str, Optional[str]]: (保存されたファイルパス, OCR結果ファイルパス)
        OCRを実行しない場合、第2要素はNone

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

            ocr_report_path = None

            # OCR分析を実行
            if ocr:
                # APIキーの取得
                if not ocr_api_key:
                    ocr_api_key = os.environ.get('GLM_API_KEY')
                    if not ocr_api_key:
                        raise ValueError("APIキーが指定されていません。--ocr-api-keyオプション、環境変数GLM_API_KEY、または.envファイルで設定してください。")

                # OCR実行
                ocr_result = perform_ocr(
                    output_path,
                    ocr_api_key,
                    languages=ocr_lang,
                    model=ocr_model
                )

                # 出力ファイルパスの決定
                if ocr_output is None:
                    # 拡張子からフォーマットを判定
                    ext = '.md'
                    if ocr_format == 'json':
                        ext = '.json'
                    elif ocr_format == 'text':
                        ext = '.txt'
                    ocr_output_path = f'ocr_report-{datetime.now().strftime("%Y%m%dT%H%M%S")}.md'
                else:
                    ocr_output_path = ocr_output

                # レポート生成
                report = generate_ocr_report(
                    ocr_result,
                    output_path,
                    url,
                    format_type=ocr_format
                )

                # レポート保存
                with open(ocr_output_path, 'w', encoding='utf-8') as f:
                    f.write(report)

                ocr_report_path = ocr_output_path

                # エラーがあれば表示
                if "error" in ocr_result:
                    print(f"警告: OCR分析中にエラーが発生しました: {ocr_result['error']}")

            return output_path, ocr_report_path

        finally:
            await browser.close()


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
  python web_snapshot.py https://example.com
  python web_snapshot.py example.com --width 1280 --height 720
  python web_snapshot.py https://example.com --output my-screenshot.png
  python web_snapshot.py https://example.com --viewport --wait 2000
  python web_snapshot.py https://example.com --ocr
  python web_snapshot.py https://example.com --ocr --ocr-format json
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
        エラー時は (1, None, None) を返す
    """
    # オプションのバリデーション
    exit_code, error_msg = validate_options(args)
    if exit_code != 0:
        return exit_code, error_msg, None

    # URLのバリデーション
    if not is_valid_url(args.url):
        return 1, f"エラー: 無効なURL '{args.url}'", None

    # URLを正規化
    normalized_url = normalize_url(args.url)

    try:
        saved_path, ocr_path = await take_screenshot(
            normalized_url,
            output_path=args.output,
            width=args.width,
            height=args.height,
            wait=args.wait,
            full_page=not args.viewport,  # --viewport指定時のみビューポートのみ
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

    exit_code, screenshot_path, ocr_path = await run_screenshot(args)

    if exit_code == 0:
        print(f"スクリーンショットを保存しました: {screenshot_path}")
        if args.ocr and ocr_path:
            print(f"OCR結果を保存しました: {ocr_path}")
    else:
        print(screenshot_path)  # この場合はエラーメッセージ

    return exit_code


def cli():
    """コンソールスクリプト用エントリーポイント（同期ラッパー）。"""
    sys.exit(asyncio.run(main()))


if __name__ == '__main__':
    cli()
