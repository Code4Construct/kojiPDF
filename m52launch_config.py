from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SUPPORTED_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class LaunchConfig:
    config_path: str
    mode: str
    auto_start: bool
    write_error_report: bool
    input_folder: str
    output_pdf: str
    settings: dict[str, Any]


class LaunchConfigError(ValueError):
    pass


def load_launch_config(config_path: str | os.PathLike[str]) -> LaunchConfig:
    path = Path(config_path).expanduser()
    if not path.exists():
        raise LaunchConfigError(f"JSON config file was not found: {path}")
    if not path.is_file():
        raise LaunchConfigError(f"JSON config path is not a file: {path}")

    try:
        with path.open("r", encoding="utf-8-sig") as file:
            data = json.load(file)
    except json.JSONDecodeError as exc:
        raise LaunchConfigError(f"JSON config file is invalid: {path}\n{exc}") from exc
    except OSError as exc:
        raise LaunchConfigError(f"JSON config file could not be read: {path}\n{exc}") from exc

    if not isinstance(data, dict):
        raise LaunchConfigError("JSON config root must be an object.")

    schema_version = data.get("schema_version", SUPPORTED_SCHEMA_VERSION)
    if schema_version != SUPPORTED_SCHEMA_VERSION:
        raise LaunchConfigError(
            f"Unsupported schema_version: {schema_version} "
            f"(supported: {SUPPORTED_SCHEMA_VERSION})"
        )

    mode = str(data.get("mode") or data.get("preset") or "mail")
    run = _object_value(data, "run")
    auto_start = bool(run.get("auto_start", False))
    write_error_report = bool(run.get("write_error_report", True))

    paths = _object_value(data, "paths")
    input_folder = paths.get("input_folder", data.get("input_folder"))
    output_pdf = paths.get("output_pdf", data.get("output_file"))

    if not input_folder:
        raise LaunchConfigError("paths.input_folder is required.")
    if not output_pdf:
        raise LaunchConfigError("paths.output_pdf is required.")

    input_folder_path = Path(str(input_folder)).expanduser()
    if not input_folder_path.exists() or not input_folder_path.is_dir():
        raise LaunchConfigError(f"Input folder was not found: {input_folder_path}")

    output_pdf_path = Path(str(output_pdf)).expanduser()
    if output_pdf_path.suffix.lower() != ".pdf":
        output_pdf_path = output_pdf_path.with_suffix(".pdf")

    output_dir = output_pdf_path.parent
    if str(output_dir) and not output_dir.exists():
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise LaunchConfigError(f"Output folder could not be created: {output_dir}\n{exc}") from exc

    settings = _object_value(data, "settings")

    return LaunchConfig(
        config_path=str(path.resolve()),
        mode=mode,
        auto_start=auto_start,
        write_error_report=write_error_report,
        input_folder=str(input_folder_path.resolve()),
        output_pdf=str(output_pdf_path.resolve()),
        settings=dict(settings),
    )


def _object_value(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key, {})
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise LaunchConfigError(f"{key} must be an object.")
    return value
