import argparse
import sys
from pathlib import Path
from typing import Any, Dict

import requests

from dandan_api import ConfigError, calculate_file_hash, load_config, match_video


def print_match_result(result: Dict[str, Any]) -> None:
    print(f"success: {result.get('success')}")
    print(f"errorCode: {result.get('errorCode')}")
    print(f"errorMessage: {result.get('errorMessage') or ''}")
    print(f"isMatched: {result.get('isMatched')}")

    matches = result.get("matches") or []
    if not matches:
        print("matches: none")
        return

    print("matches:")
    for index, item in enumerate(matches, start=1):
        print(f"[{index}]")
        print(f"  animeTitle: {item.get('animeTitle') or ''}")
        print(f"  episodeTitle: {item.get('episodeTitle') or ''}")
        print(f"  episodeId: {item.get('episodeId')}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Match a local video file with dandanplay episodes."
    )
    parser.add_argument("video_path", help="Path to a local video file")
    parser.add_argument(
        "--config",
        help="Path to config.json. Defaults to config.json next to main.py.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    video_path = Path(args.video_path)

    if not video_path.is_file():
        print(f"File not found: {video_path}", file=sys.stderr)
        return 1

    file_name = video_path.name
    file_size = video_path.stat().st_size
    file_hash = calculate_file_hash(video_path)

    print(f"fileName: {file_name}")
    print(f"fileSize: {file_size}")
    print(f"fileHash: {file_hash}")

    try:
        config = load_config(Path(args.config) if args.config else None)
        result = match_video(
            file_name=file_name,
            file_size=file_size,
            file_hash=file_hash,
            config=config,
        )
    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 2
    except requests.HTTPError as exc:
        response = exc.response
        detail = response.text if response is not None else str(exc)
        print(f"HTTP error: {detail}", file=sys.stderr)
        return 3
    except requests.RequestException as exc:
        print(f"Request error: {exc}", file=sys.stderr)
        return 3

    print_match_result(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
