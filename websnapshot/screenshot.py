"""
Screenshot functionality for Web Snapshot Tool.

Playwrightを使用してWebページのスクリーンショットを取得する機能を提供します。
"""

import os
import base64
from datetime import datetime
from typing import Optional

from playwright.async_api import async_playwright, Error as PlaywrightError

from websnapshot.utils import generate_filename
from websnapshot.ocr import perform_ocr, generate_ocr_report


async def _wait_for_page_stabilization(page, max_iterations: int = 15, stable_iterations: int = 3) -> None:
    """
    ページの高さが安定するまで待機し、lazy loadingをトリガーする。
    フッターなどの遅延読み込みコンテンツも確実に読み込む。

    Args:
        page: Playwrightページオブジェクト
        max_iterations: 最大スキャン回数
        stable_iterations: 高さが安定したと判定する回数
    """
    last_height = 0
    stable_count = 0
    iteration = 0

    while iteration < max_iterations:
        current_height = await page.evaluate('document.documentElement.scrollHeight')

        if current_height != last_height:
            stable_count = 0
            last_height = current_height

            await page.evaluate('''
                window.scrollTo(0, document.documentElement.scrollHeight);
            ''')
            await page.wait_for_timeout(500)
        else:
            stable_count += 1

        if stable_count >= stable_iterations:
            break

        iteration += 1

    # 安定後、フッター等の遅延コンテンツを確実に読み込む
    await page.evaluate('window.scrollTo(0, document.body.scrollHeight);')
    await page.wait_for_timeout(2000)

    await page.evaluate('window.scrollTo(0, document.body.scrollHeight);')
    await page.wait_for_timeout(2000)

    await page.evaluate('window.scrollTo(0, Math.max(0, document.body.scrollHeight - 500));')
    await page.wait_for_timeout(500)
    await page.evaluate('window.scrollTo(0, document.body.scrollHeight);')
    await page.wait_for_timeout(1500)

    # 最後にトップに戻す
    await page.evaluate('window.scrollTo(0, 0);')
    await page.wait_for_timeout(300)


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
        ValueError: APIキーが指定されていない場合
    """
    if output_path is None:
        output_path = generate_filename()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        try:
            page = await browser.new_page(viewport={'width': width, 'height': height})

            # ページ読み込み
            await page.goto(url, wait_until='domcontentloaded', timeout=60000)

            if wait is not None and wait > 0:
                await page.wait_for_timeout(wait)

            if full_page:
                await _wait_for_page_stabilization(page)

            # CDPを使用してスクリーンショット（Playwrightのフォント待機を回避）
            cdp = await page.context.new_cdp_session(page)

            if full_page:
                # ページ全体のサイズを取得
                layout = await cdp.send('Page.getLayoutMetrics')
                content_width = int(layout['contentSize']['width'])
                content_height = int(layout['contentSize']['height'])

                # ビューポートをページ全体に拡大してコンテンツを全てレンダリングさせる
                await cdp.send('Emulation.setDeviceMetricsOverride', {
                    'mobile': False,
                    'width': content_width,
                    'height': content_height,
                    'deviceScaleFactor': 1,
                })
                await page.wait_for_timeout(500)

                # フルページスクリーンショット
                result = await cdp.send('Page.captureScreenshot', {
                    'format': 'png',
                    'captureBeyondViewport': True,
                })

                # ビューポートをリセット
                await cdp.send('Emulation.clearDeviceMetricsOverride')
            else:
                # ビューポートのみキャプチャ
                result = await cdp.send('Page.captureScreenshot', {
                    'format': 'png',
                    'clip': {
                        'x': 0,
                        'y': 0,
                        'width': width,
                        'height': height,
                        'scale': 1
                    }
                })

            # Base64データをデコードして保存
            screenshot_data = base64.b64decode(result['data'])
            with open(output_path, 'wb') as f:
                f.write(screenshot_data)

            await cdp.detach()

            ocr_report_path = None

            if ocr:
                if not ocr_api_key:
                    ocr_api_key = os.environ.get('GLM_API_KEY')
                    if not ocr_api_key:
                        raise ValueError("APIキーが指定されていません。--ocr-api-keyオプション、環境変数GLM_API_KEY、または.envファイルで設定してください。")

                ocr_result = perform_ocr(
                    output_path,
                    ocr_api_key,
                    languages=ocr_lang,
                    model=ocr_model
                )

                if ocr_output is None:
                    ext = '.md'
                    if ocr_format == 'json':
                        ext = '.json'
                    elif ocr_format == 'text':
                        ext = '.txt'
                    ocr_output_path = f'ocr_report-{datetime.now().strftime("%Y%m%dT%H%M%S")}{ext}'
                else:
                    ocr_output_path = ocr_output

                report = generate_ocr_report(
                    ocr_result,
                    output_path,
                    url,
                    format_type=ocr_format
                )

                with open(ocr_output_path, 'w', encoding='utf-8') as f:
                    f.write(report)

                ocr_report_path = ocr_output_path

                if "error" in ocr_result:
                    print(f"警告: OCR分析中にエラーが発生しました: {ocr_result['error']}")

            return output_path, ocr_report_path

        finally:
            await browser.close()
