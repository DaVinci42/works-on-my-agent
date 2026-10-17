import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from collections.abc import Mapping
from http.client import HTTPResponse
from pathlib import Path
from typing import cast

ENDPOINT = "https://api.githubcopilot.com/models"
TTL = 86400
MAX_STALE = 7 * TTL
CATEGORY_RANK = {"lightweight": 0, "versatile": 1, "powerful": 2}


def mapping(value: object) -> Mapping[str, object]:
    return cast(Mapping[str, object], value) if isinstance(value, dict) else {}


def string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [
        entry for entry in cast(list[object], value) if isinstance(entry, str) and entry
    ]


def discover(payload: object, known: set[str]) -> list[dict[str, object]]:
    records = mapping(payload).get("data")
    if not isinstance(records, list):
        raise TypeError("Model response must contain a data array")
    candidates: list[dict[str, object]] = []
    for entry in cast(list[object], records):
        model = mapping(entry)
        identifier = model.get("id")
        capabilities = mapping(model.get("capabilities"))
        supports = mapping(capabilities.get("supports"))
        if (
            not isinstance(identifier, str)
            or "copilot/" + identifier not in known
            or model.get("model_picker_enabled") is not True
            or capabilities.get("type") != "chat"
            or supports.get("tool_calls") is not True
            or mapping(model.get("policy")).get("state") not in (None, "enabled")
        ):
            continue
        limits = mapping(capabilities.get("limits"))
        candidates.append(
            {
                "model": "copilot/" + identifier,
                "category": model.get("model_picker_category") or "unknown",
                "reasoning_effort": string_list(supports.get("reasoning_effort")),
                "context_window": limits.get("max_context_window_tokens"),
                "max_output_tokens": limits.get("max_output_tokens"),
            }
        )
    return sorted(candidates, key=model_rank)


def model_rank(model: Mapping[str, object]) -> tuple[int, str]:
    return CATEGORY_RANK.get(str(model.get("category")), 3), str(model["model"])


def command(arguments: list[str], timeout: float) -> str:
    return subprocess.run(
        arguments, check=True, capture_output=True, text=True, timeout=timeout
    ).stdout.strip()


def fetch(timeout: float) -> list[dict[str, object]]:
    token = command(["gh", "auth", "token", "--hostname", "github.com"], timeout)
    if not token:
        raise ValueError("Empty GitHub token")
    known = set(command(["crush", "models"], timeout).splitlines())
    request = urllib.request.Request(
        ENDPOINT,
        headers={
            "Authorization": "Bearer " + token,
            "Copilot-Integration-Id": "copilot-developer-cli",
        },
    )
    with cast(
        HTTPResponse, urllib.request.urlopen(request, timeout=timeout)
    ) as response:
        return discover(cast(object, json.load(response)), known)


def cached_models(
    path: Path, refresh: bool, timeout: float
) -> tuple[list[dict[str, object]], str]:
    cached: list[dict[str, object]] | None = None
    age = float("inf")
    try:
        data = mapping(cast(object, json.loads(path.read_text())))
        timestamp, models = data.get("fetched_at"), data.get("models")
        if isinstance(timestamp, (int, float)) and isinstance(models, list):
            entries = cast(list[object], models)
            if all(isinstance(mapping(entry).get("model"), str) for entry in entries):
                cached = [dict(mapping(entry)) for entry in entries]
                age = time.time() - timestamp
    except (OSError, ValueError):
        pass
    if cached is not None and 0 <= age < TTL and not refresh:
        return cached, "fresh"
    try:
        candidates = fetch(timeout)
    except (OSError, ValueError, TypeError, subprocess.SubprocessError):
        if cached is not None and 0 <= age <= MAX_STALE and not refresh:
            print(
                "Warning: refresh failed; using stale model catalog.", file=sys.stderr
            )
            return cached, "stale"
        raise
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", dir=path.parent, delete=False
        ) as stream:
            temporary = Path(stream.name)
            json.dump({"fetched_at": time.time(), "models": candidates}, stream)
        _ = temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return candidates, "refreshed"


class Arguments(argparse.Namespace):
    refresh: bool = False
    timeout: float = 30
    category: str | None = None


def error_reason(error: Exception) -> str:
    if isinstance(error, subprocess.SubprocessError):
        cmd = getattr(error, "cmd", None)
        binary = (
            str(cast(list[object], cmd)[0])
            if isinstance(cmd, list) and cmd
            else "command"
        )
        return f"{type(error).__name__} ({Path(binary).name})"
    if isinstance(error, urllib.error.HTTPError):
        return f"HTTPError ({error.code})"
    return type(error).__name__


def main() -> int:
    parser = argparse.ArgumentParser(
        description="List cached Copilot worker candidates known to Crush."
    )
    _ = parser.add_argument(
        "--refresh",
        action="store_true",
        help="Refresh after account or Crush configuration changes; fail rather than reuse old data.",
    )
    _ = parser.add_argument("--timeout", type=float, default=30)
    _ = parser.add_argument(
        "--category", choices=("lightweight", "versatile", "powerful")
    )
    args = parser.parse_args(namespace=Arguments())
    if not 0 < args.timeout < float("inf"):
        parser.error("--timeout must be finite and positive")
    root = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")
    try:
        models, state = cached_models(
            root / "crush-copilot-delegate" / "models.json", args.refresh, args.timeout
        )
        if args.category:
            models = [
                model for model in models if model.get("category") == args.category
            ]
        print(
            json.dumps(
                {"cache": state, "models": sorted(models, key=model_rank)}, indent=2
            )
        )
        return 0 if models else 2
    except (OSError, ValueError, TypeError, subprocess.SubprocessError) as error:
        print(
            f"Discovery failed ({error_reason(error)}): check GitHub authentication, network, Crush CLI, and cache permissions.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
