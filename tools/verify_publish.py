"""Fail closed if a public tree contains unexpected files or identifying text."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


BLOCKED = re.compile(
    r"(?i)([\w.+-]+@(?!users\.noreply\.github\.com)[\w.-]+\.[a-z]{2,}|"
    r"[A-Z]:\\Users\\(?!SampleUser\\)[^\\\s]+|"
    r"[A-Z]:[/\\]01[^/\\\s]+|"
    r"[A-Z]:[/\\][^\r\n]*?のデータ[/\\][^\r\n]*)"
)
TEXT_SUFFIXES = {".py", ".md", ".txt", ".bat", ".yml", ".yaml", ".wxs", ".json"}


def verify_bytes(files: dict[str, bytes]) -> None:
    failures = []
    for name, raw in files.items():
        if BLOCKED.search(name):
            failures.append(f"identifying filename: {name}")
        if Path(name).suffix.lower() in TEXT_SUFFIXES:
            text = raw.decode("utf-8-sig")
            for number, line in enumerate(text.splitlines(), 1):
                if BLOCKED.search(line):
                    failures.append(f"identifying text: {name}:{number}")
    if failures:
        raise ValueError("Publication check failed:\n" + "\n".join(failures))


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "publish-manifest.json").read_text(encoding="utf-8"))
    expected = set(manifest["files"])
    if (root / ".git").is_dir():
        result = subprocess.run(["git", "-C", str(root), "ls-files", "-z"],
                                check=True, capture_output=True)
        actual = {name.decode("utf-8") for name in result.stdout.split(b"\0") if name}
    else:
        actual = {p.relative_to(root).as_posix() for p in root.rglob("*")
                  if p.is_file() and ".git" not in p.relative_to(root).parts}
    extra = actual - expected
    missing = expected - actual
    if extra or missing:
        raise ValueError(f"Unexpected files: {sorted(extra)}; missing files: {sorted(missing)}")
    verify_bytes({name: (root / name).read_bytes() for name in expected})
    print(f"Publication check passed: {len(expected)} allowlisted files")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1)
