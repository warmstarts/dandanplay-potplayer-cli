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


def match_video(
    *,
    file_name: str,
    file_size: int,
    file_hash: str = "",
    config: Optional[Dict[str, str]] = None,
    timeout: float = 15.0,
) -> Dict[str, Any]:
    config = config or load_config()
    url = f"{API_BASE_URL}{MATCH_PATH}"
    payload = {
        "fileName": file_name,
        "fileHash": file_hash,
        "fileSize": file_size,
    }

    response = requests.post(
        url,
        json=payload,
        headers=build_auth_headers(config, MATCH_PATH),
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()
