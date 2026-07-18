from __future__ import annotations

import shutil
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath


SUPPORTED_ZIP_EXTENSIONS = {".zip"}


@dataclass
class ZipExtractionResult:
    success: bool
    source: Path
    output: Path | None = None
    error: str | None = None


def unique_directory(parent: Path, name: str) -> Path:
    safe_name = "".join(char for char in name if char not in '<>:"/\\|?*').strip()
    safe_name = safe_name.rstrip(". ")
    if not safe_name:
        safe_name = "zip"

    candidate = parent / safe_name
    if not candidate.exists():
        return candidate

    index = 1
    while True:
        candidate = parent / f"{safe_name}_{index}"
        if not candidate.exists():
            return candidate
        index += 1


def safe_member_parts(member_name: str) -> tuple[str, ...]:
    normalized_name = member_name.replace("\\", "/")
    if normalized_name.startswith("/"):
        raise RuntimeError(f"安全でないZIP内パスです: {member_name}")

    parts = PurePosixPath(normalized_name).parts
    safe_parts = []
    for part in parts:
        if part in ("", "."):
            continue
        if part == ".." or ":" in part:
            raise RuntimeError(f"安全でないZIP内パスです: {member_name}")
        safe_parts.append(part)

    if not safe_parts:
        raise RuntimeError(f"空のZIP内パスです: {member_name}")
    return tuple(safe_parts)


def ensure_inside_directory(target_path: Path, base_path: Path) -> None:
    target_resolved = target_path.resolve()
    base_resolved = base_path.resolve()
    if target_resolved != base_resolved and base_resolved not in target_resolved.parents:
        raise RuntimeError(f"展開先フォルダ外への書き込みを拒否しました: {target_path}")


def extract_zip_file(zip_path: str | Path, delete_source: bool = True) -> ZipExtractionResult:
    zip_path = Path(zip_path)
    output_dir = unique_directory(zip_path.parent, zip_path.stem)

    try:
        with zipfile.ZipFile(zip_path) as zip_file:
            for info in zip_file.infolist():
                if info.flag_bits & 0x1:
                    raise RuntimeError("パスワード付きZIPには対応していません。")

            output_dir.mkdir(parents=True, exist_ok=False)
            for info in zip_file.infolist():
                parts = safe_member_parts(info.filename)
                target_path = output_dir.joinpath(*parts)
                ensure_inside_directory(target_path, output_dir)

                if info.is_dir():
                    target_path.mkdir(parents=True, exist_ok=True)
                    continue

                target_path.parent.mkdir(parents=True, exist_ok=True)
                with zip_file.open(info) as source_file, target_path.open("wb") as destination_file:
                    shutil.copyfileobj(source_file, destination_file)

        if delete_source:
            zip_path.unlink(missing_ok=True)

        return ZipExtractionResult(success=True, source=zip_path, output=output_dir)
    except Exception as exc:
        if output_dir.exists():
            shutil.rmtree(output_dir, ignore_errors=True)
        return ZipExtractionResult(success=False, source=zip_path, output=output_dir, error=str(exc))


def extract_all_zips_in_folder(folder_path: str | Path, issue_report=None) -> list[ZipExtractionResult]:
    folder_path = Path(folder_path)
    zip_files = sorted(
        path
        for path in folder_path.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_ZIP_EXTENSIONS
    )

    results = []
    for zip_file in zip_files:
        print(f"Extracting zip file: {zip_file}")
        result = extract_zip_file(zip_file)
        results.append(result)
        if result.success:
            print(f"Zip extraction complete: {result.output}")
            continue

        message = f"ZIPファイルの展開に失敗しました: {result.source} -> {result.error}"
        print(message)
        if issue_report is not None:
            issue_report.append(
                {
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "category": "Zip extraction error",
                    "message": message,
                }
            )

    return results
