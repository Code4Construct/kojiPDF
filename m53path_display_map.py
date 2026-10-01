from __future__ import annotations

import json
from pathlib import Path


MAP_FILE_NAME = ".kojipdf_display_map.json"


def safe_unicode_text(value, replacement: str = "\ufffd") -> str:
    return "".join(
        replacement if 0xD800 <= ord(char) <= 0xDFFF else char
        for char in str(value or "")
    )


def normalize_relative_path(path) -> str:
    return Path(path).as_posix().strip("/")


def map_file_path(root_path) -> Path:
    return Path(root_path) / MAP_FILE_NAME


def load_display_map(root_path) -> dict[str, str]:
    path = map_file_path(root_path)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(key): safe_unicode_text(value) for key, value in data.items()}


def save_display_map(root_path, display_map: dict[str, str]) -> None:
    path = map_file_path(root_path)
    safe_map = {str(key): safe_unicode_text(value) for key, value in display_map.items()}
    path.write_text(
        json.dumps(safe_map, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
        errors="replace",
    )


def find_map_root(path) -> Path | None:
    current = Path(path).resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if map_file_path(candidate).exists():
            return candidate
    return None


def set_display_name(path, display_name: str, root_path=None) -> None:
    root = Path(root_path) if root_path is not None else find_map_root(path)
    if root is None:
        return
    try:
        relative_path = Path(path).resolve().relative_to(root.resolve())
    except ValueError:
        return
    display_map = load_display_map(root)
    display_map[normalize_relative_path(relative_path)] = safe_unicode_text(display_name)
    save_display_map(root, display_map)


def unique_short_directory(parent, prefix: str, display_name: str) -> Path:
    parent = Path(parent)
    index = 1
    while True:
        candidate = parent / f"{prefix}{index:05d}"
        if not candidate.exists():
            candidate.mkdir(parents=True)
            set_display_name(candidate, display_name)
            return candidate
        index += 1


def unique_short_file_path(directory, prefix: str, suffix: str, display_name: str) -> Path:
    directory = Path(directory)
    suffix = suffix.lower()
    used_stems = {path.stem.casefold() for path in directory.iterdir()} if directory.exists() else set()
    index = 1
    while True:
        candidate = directory / f"{prefix}{index:05d}{suffix}"
        if candidate.stem.casefold() not in used_stems:
            set_display_name(candidate, display_name)
            return candidate
        index += 1


def mapped_child_name(parent_relative_path: str, child_actual_name: str, display_map: dict[str, str]) -> str:
    relative_path = normalize_relative_path(Path(parent_relative_path) / child_actual_name)
    return display_map.get(relative_path, child_actual_name)


def mapped_relative_path(relative_path, display_map: dict[str, str]) -> Path:
    parts = []
    parent_relative = ""
    for part in Path(relative_path).parts:
        parts.append(mapped_child_name(parent_relative, part, display_map))
        parent_relative = normalize_relative_path(Path(parent_relative) / part)
    return Path(*parts) if parts else Path()


def map_pdf_sidecar_name(relative_pdf_path: str, source_name: str, display_map: dict[str, str]) -> None:
    pdf_path = normalize_relative_path(relative_pdf_path)
    source_display = display_map.get(normalize_relative_path(source_name), Path(source_name).name)
    display_map[pdf_path] = str(Path(source_display).with_suffix(".pdf"))
