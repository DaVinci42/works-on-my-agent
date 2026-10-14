#!/usr/bin/env bash
set -euo pipefail

# Read-only, sanitized signal collector for evolving the mdatp-optimization skill.
# Extracts command shapes and toolchain frequencies from shell history without
# exposing personal paths, arguments, tokens, or machine identifiers.

python3 - <<'PY'
import collections
import pathlib
import re
import subprocess

home = pathlib.Path.home()
history_files = [
    home / ".zsh_history",
    home / ".bash_history",
    home / ".local/state/zsh/history",
]

cmds = []
for fp in history_files:
    if not fp.exists():
        continue
    raw = fp.read_bytes().decode("utf-8", errors="replace")
    for line in raw.splitlines():
        if line.startswith(":") and ";" in line:
            line = line.split(";", 1)[1]
        line = line.strip()
        if line:
            cmds.append(line)

def sanitize(text: str) -> str:
    text = text.replace(str(home), "$HOME")
    text = re.sub(r"/Users/[A-Za-z0-9._-]+", "/Users/<user>", text)
    text = re.sub(r"/nix/store/[a-z0-9]{32}-", "/nix/store/<hash>-", text)
    text = re.sub(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
        "<UUID>",
        text,
    )
    return text

print(f"=== 1. Shell History Summary ({len(cmds)} commands scanned) ===")
mdatp_shapes = collections.Counter()
for c in cmds:
    if "mdatp" in c or "wdav" in c or "Defender" in c:
        s = sanitize(c).rstrip("\\").strip()
        mdatp_shapes[s] += 1

print("\n--- Historical mdatp / Defender commands (sanitized) ---")
for cmd_str, count in mdatp_shapes.most_common(30):
    print(f"  [{count}x] {cmd_str[:120]}")

toolchains = [
    "git", "nix", "darwin-rebuild", "home-manager", "cargo", "rustc",
    "xcodebuild", "swift", "gradle", "adb", "npm", "pnpm", "bun", "volta",
    "python3", "uv", "pytest", "go", "docker", "podman", "colima", "orbstack",
    "claude", "codex", "crush", "opencode", "gh", "cmake", "ninja",
]
tc_counts = collections.Counter()
for c in cmds:
    tokens = re.findall(r"\b[a-zA-Z0-9_-]+\b", c[:80])
    for t in toolchains:
        if t in tokens:
            tc_counts[t] += 1

print("\n--- Top Active Toolchains in History ---")
for tool, count in tc_counts.most_common(20):
    print(f"  {tool}: {count}")

wdavdiag = pathlib.Path("/Library/Application Support/Microsoft/Defender/wdavdiag")
if wdavdiag.exists():
    zips = list(wdavdiag.glob("*.zip"))
    total_mb = sum(z.stat().st_size for z in zips) / (1024 * 1024)
    print(f"\n=== 2. Diagnostic Bundle Storage (/Library/Application Support/Microsoft/Defender/wdavdiag) ===")
    print(f"  Bundle count: {len(zips)}, Total size: {total_mb:.1f} MB")
PY
