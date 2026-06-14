import base64
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

import requests


API_BASE_URL = "https://api.dandanplay.net"
MATCH_PATH = "/api/v2/match"
COMMENT_PATH_TEMPLATE = "/api/v2/comment/{episode_id}"
COMMENT_QUERY_PARAMS = {
    "withRelated": "true",
    "chConvert": 1,
}
DANDANPLAY_HASH_BYTES = 16 * 1024 * 1024


class ConfigError(RuntimeError):
    pass


def load_config(config_path: Optional[Path] = None) -> Dict[str, str]:
    config_path = config_path or Path(__file__).with_name("config.json")
    config: Dict[str, str] = {}

    if config_path.exists():
        with config_path.open("r", encoding="utf-8") as f:
            raw_config = json.load(f)
        config.update({k: str(v) for k, v in raw_config.items() if v is not None})

    env_map = {
        "app_id": "DANDANPLAY_APP_ID",
        "app_secret": "DANDANPLAY_APP_SECRET",
        "auth_mode": "DANDANPLAY_AUTH_MODE",
    }
    for key, env_name in env_map.items():
        value = os.getenv(env_name)
        if value:
            config[key] = value

    return config


def generate_signature(app_id: str, timestamp: int, path: str, app_secret: str) -> str:
    data = f"{app_id}{timestamp}{path}{app_secret}"
    digest = hashlib.sha256(data.encode("utf-8")).digest()
    return base64.b64encode(digest).decode("ascii")


def build_auth_headers(config: Dict[str, str], path: str) -> Dict[str, str]:
    app_id = config.get("app_id", "").strip()
    app_secret = config.get("app_secret", "").strip()
    auth_mode = config.get("auth_mode", "secret").strip().lower()

    if not app_id:
        raise ConfigError("missing app_id: set it in config.json or DANDANPLAY_APP_ID")
    if not app_secret:
        raise ConfigError(
            "missing app_secret: set it in config.json or DANDANPLAY_APP_SECRET"
        )

    headers = {"X-AppId": app_id}

    if auth_mode == "signature":
        timestamp = int(time.time())
        headers["X-Timestamp"] = str(timestamp)
        headers["X-Signature"] = generate_signature(
            app_id=app_id,
            timestamp=timestamp,
            path=path.lower(),
            app_secret=app_secret,
        )
    elif auth_mode == "secret":
        headers["X-AppSecret"] = app_secret
    else:
        raise ConfigError("auth_mode must be 'secret' or 'signature'")

    return headers


def calculate_file_hash(video_path: Path) -> str:
    """Return the dandanplay fileHash: MD5 of the first 16 MiB."""
    md5 = hashlib.md5()
    with video_path.open("rb") as f:
        md5.update(f.read(DANDANPLAY_HASH_BYTES))
    return md5.hexdigest()


def match_video(
    *,
    file_name: str,
    file_size: int,
    file_hash: str = "",
    config: Optional[Dict[str, str]] = None,
    timeout: float = 15.0,
) -> Dict[str, Any]:
    if config is None:
        config = load_config()
    url = f"{API_BASE_URL}{MATCH_PATH}"
    payload = {
        "fileName": file_name,
        "fileHash": file_hash,
        "fileSize": file_size,
    }

    print("payload:")
    print(json.dumps(payload, ensure_ascii=False, indent=2))

    response = requests.post(
        url,
        json=payload,
        headers=build_auth_headers(config, MATCH_PATH),
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()


def build_comment_url(episode_id: int) -> str:
    path = COMMENT_PATH_TEMPLATE.format(episode_id=episode_id)
    return requests.Request(
        "GET",
        f"{API_BASE_URL}{path}",
        params=COMMENT_QUERY_PARAMS,
    ).prepare().url


def fetch_comments(
    *,
    episode_id: int,
    config: Dict[str, str],
    timeout: float = 30.0,
) -> Any:
    path = COMMENT_PATH_TEMPLATE.format(episode_id=episode_id)
    url = build_comment_url(episode_id)
    print(f"comment request: GET {url}")

    response = requests.get(
        url,
        headers=build_auth_headers(config, path),
        allow_redirects=True,
        timeout=timeout,
    )
    response.raise_for_status()
    comment_result = response.json()
    print_comment_structure(comment_result)
    return comment_result


def print_comment_structure(comment_result: Any) -> None:
    print(f"comment_result type: {type(comment_result).__name__}")

    if isinstance(comment_result, dict):
        print(f"comment_result keys: {list(comment_result.keys())}")
        print("comment_result key types:")
        for key, value in comment_result.items():
            print(f"  {key}: {type(value).__name__}")
        data = comment_result.get("data")
        if isinstance(data, dict):
            print(f"comment_result data keys: {list(data.keys())}")
    elif isinstance(comment_result, list):
        print(f"comment_result length: {len(comment_result)}")
        print("comment_result first 3 items:")
        for index, item in enumerate(comment_result[:3], start=1):
            print(f"  [{index}] {item!r}")
