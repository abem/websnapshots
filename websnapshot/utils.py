"""
Utility functions for Web Snapshot Tool.

URL検証、正規化、ファイル名生成などのユーティリティ機能を提供します。
"""

import base64
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse


def load_env_file() -> None:
    """
    .envファイルから環境変数を読み込む。

    優先順位: カレントディレクトリ > スクリプトディレクトリ > ホームディレクトリ
    """
    try:
        from dotenv import load_dotenv

        script_dir = Path(__file__).parent.parent
        home_dir = Path.home()

        env_paths = [
            Path('.env'),
            script_dir / '.env',
            home_dir / '.websnapshots' / '.env',
            home_dir / '.env',
        ]

        for env_path in env_paths:
            if env_path.exists():
                load_dotenv(env_path, override=True)
                break
    except ImportError:
        pass


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

    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    try:
        result = urlparse(url)
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


# モジュール読み込み時に.envをロード
load_env_file()
