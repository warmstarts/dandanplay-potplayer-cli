import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import requests

from dandan_api import (
    ConfigError,
    calculate_file_hash,
    fetch_comments,
    load_config,
    match_video,
)


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


def pick_episode_id(result: Dict[str, Any]) -> Optional[int]:
    if not result.get("success", False):
        return None

    matches = result.get("matches") or []
    for item in matches:
        episode_id = item.get("episodeId")
        if episode_id is not None:
            try:
                return int(episode_id)
            except (TypeError, ValueError):
                continue
    return None


def extract_comment_list(comment_result: Any) -> Optional[list]:
    if isinstance(comment_result, list):
        return comment_result

    if not isinstance(comment_result, dict):
        return None

    for key in ("comments", "comment", "items", "results"):
        value = comment_result.get(key)
        if isinstance(value, list):
            return value

    data = comment_result.get("data")
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        nested_comments = extract_comment_list(data)
        if nested_comments is not None:
            return nested_comments

    if {"cid", "p", "m"}.intersection(comment_result.keys()):
        return [comment_result]

    return None


def get_comment_count(comment_result: Any) -> int:
    comments = extract_comment_list(comment_result)
    if comments is not None:
        return len(comments)
    return 0


def save_raw_comments(video_path: Path, comment_result: Any) -> Path:
    output_path = video_path.with_name(f"{video_path.name}.dandan.json")
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(comment_result, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return output_path


def print_comment_http_error(exc: requests.HTTPError) -> None:
    response = exc.response
    print("Comment HTTP error:", file=sys.stderr)
    if response is None:
        print(f"  {exc}", file=sys.stderr)
        return

    print(f"  status_code: {response.status_code}", file=sys.stderr)
    print(f"  reason: {response.reason}", file=sys.stderr)
    print(f"  final_url: {response.url}", file=sys.stderr)
    print("  response.headers:", file=sys.stderr)
    for key, value in response.headers.items():
        print(f"    {key}: {value}", file=sys.stderr)
    print("  response.text first 1000 chars:", file=sys.stderr)
    print(response.text[:1000], file=sys.stderr)


def print_comment_api_error(comment_result: Dict[str, Any]) -> None:
    print("Comment API returned success=false.", file=sys.stderr)
    print("full JSON:", file=sys.stderr)
    print(json.dumps(comment_result, ensure_ascii=False, indent=2), file=sys.stderr)

    known_fields = {"success", "errorCode", "errorMessage", "message", "code"}
    print("known fields:", file=sys.stderr)
    for key in ("success", "errorCode", "errorMessage", "message", "code"):
        print(f"  {key}: {comment_result.get(key)}", file=sys.stderr)

    other_fields = [key for key in comment_result.keys() if key not in known_fields]
    print("other top-level fields:", file=sys.stderr)
    if other_fields:
        for key in other_fields:
            print(f"  {key}: {comment_result.get(key)!r}", file=sys.stderr)
    else:
        print("  none", file=sys.stderr)

    data = comment_result.get("data")
    if isinstance(data, dict):
        data_keys = list(data.keys())
        print(f"data keys: {data_keys}", file=sys.stderr)


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

    if not result.get("success", False):
        error_message = result.get("errorMessage") or "unknown match API error"
        print(f"Match API returned success=false: {error_message}", file=sys.stderr)
        return 4

    episode_id = pick_episode_id(result)
    if episode_id is None:
        print("No matched episodeId found.", file=sys.stderr)
        return 4

    try:
        comment_result = fetch_comments(episode_id=episode_id, config=config)
    except requests.HTTPError as exc:
        print_comment_http_error(exc)
        return 5
    except requests.RequestException as exc:
        print(f"Comment request error: {exc}", file=sys.stderr)
        return 5

    if isinstance(comment_result, dict) and comment_result.get("success") is False:
        print_comment_api_error(comment_result)
        return 6

    comment_count = get_comment_count(comment_result)
    if comment_count == 0:
        print("No comments found.", file=sys.stderr)
        return 6

    try:
        output_path = save_raw_comments(video_path, comment_result)
    except OSError as exc:
        print(f"Failed to save comments: {exc}", file=sys.stderr)
        return 7

    print(f"commentCount: {comment_count}")
    print(f"saved: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
