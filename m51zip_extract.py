from __future__ import annotations

import shutil
import zipfile
import re
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


def decoded_member_name(info: zipfile.ZipInfo) -> str:
    if info.flag_bits & 0x800:
        return info.filename

    raw_name = info.filename.encode("cp437")
    try:
        return raw_name.decode("cp932")
    except UnicodeError:
        pass

    try:
        return raw_name.replace(b"/", b"\\").decode("cp932")
    except UnicodeError:
        return info.filename


def has_single_top_level_folder(members: list[tuple[zipfile.ZipInfo, tuple[str, ...]]]) -> bool:
    top_level_names = {parts[0] for _, parts in members}
    if len(top_level_names) != 1:
        return False

    return all(len(parts) > 1 or info.is_dir() for info, parts in members)


def carry_attachment_prefix(zip_stem: str, folder_name: str) -> str:
    match = re.match(r"^(\d{2,})(?:[_\-\s]+)?", zip_stem)
    if not match:
        return folder_name

    number = match.group(1)
    if folder_name.startswith(number):
        return folder_name
    return f"{number}_{folder_name}"


def ensure_inside_directory(target_path: Path, base_path: Path) -> None:
    target_resolved = target_path.resolve()
    base_resolved = base_path.resolve()
    if target_resolved != base_resolved and base_resolved not in target_resolved.parents:
        raise RuntimeError(f"展開先フォルダ外への書き込みを拒否しました: {target_path}")


def extract_zip_file(zip_path: str | Path, delete_source: bool = True) -> ZipExtractionResult:
    zip_path = Path(zip_path)
    output_dir = None

    try:
        with zipfile.ZipFile(zip_path) as zip_file:
            for info in zip_file.infolist():
                if info.flag_bits & 0x1:
                    raise RuntimeError("パスワード付きZIPには対応していません。")

            members = [
                (info, safe_member_parts(decoded_member_name(info)))
                for info in zip_file.infolist()
            ]
            flatten_zip_name = has_single_top_level_folder(members)
            output_name = (
                carry_attachment_prefix(zip_path.stem, members[0][1][0])
                if flatten_zip_name
                else zip_path.stem
            )
            output_dir = unique_directory(
                zip_path.parent,
                output_name,
            )

            output_dir.mkdir(parents=True, exist_ok=False)
            for info, parts in members:
                target_parts = parts[1:] if flatten_zip_name else parts
                target_path = output_dir.joinpath(*target_parts) if target_parts else output_dir
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
        if output_dir is not None and output_dir.exists():
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
