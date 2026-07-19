from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import fitz


NON_TEXT_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".xlsm",
    ".ppt",
    ".pptx",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".tif",
    ".tiff",
    ".webp",
    ".zip",
    ".7z",
    ".rar",
    ".exe",
    ".dll",
}
TEXT_ENCODING_CANDIDATES = (
    "utf-8-sig",
    "utf-8",
    "cp932",
    "shift_jis",
    "iso-2022-jp",
    "euc-jp",
    "utf-16",
)
TEXT_SAMPLE_SIZE = 8192
MAX_TEXT_SCORE_RATIO = 0.08
BINARY_SIGNATURES = (
    b"%PDF",
    b"PK\x03\x04",
    b"PK\x05\x06",
    b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1",
    b"\xFF\xD8\xFF",
    b"\x89PNG\r\n\x1A\n",
    b"GIF87a",
    b"GIF89a",
    b"BM",
)


@dataclass
class TextConversionResult:
    success: bool
    source: Path
    output: Path | None = None
    error: str | None = None


def unique_pdf_path(text_path: Path) -> Path:
    candidate = text_path.with_suffix(".pdf")
    if not candidate.exists():
        return candidate

    index = 1
    while True:
        candidate = text_path.with_name(f"{text_path.stem}_{index}.pdf")
        if not candidate.exists():
            return candidate
        index += 1


def mojibake_score(text: str) -> int:
    bad_chars = text.count("\ufffd")
    suspicious = sum(text.count(char) for char in "縺繧譁蜿荳鬆")
    control_chars = sum(1 for char in text if ord(char) < 32 and char not in "\r\n\t")
    return bad_chars * 20 + suspicious * 2 + control_chars


def read_text_file(text_path: Path) -> str:
    data = text_path.read_bytes()
    best_text = ""
    best_score = 10**9

    for encoding in TEXT_ENCODING_CANDIDATES:
        try:
            decoded = data.decode(encoding)
        except UnicodeDecodeError:
            continue
        score = mojibake_score(decoded)
        if score < best_score:
            best_text = decoded
            best_score = score
            if score == 0:
                break

    if best_text:
        return best_text
    return data.decode("utf-8", errors="replace")


def is_probably_text_file(path: Path) -> bool:
    if path.suffix.lower() in NON_TEXT_EXTENSIONS:
        return False

    try:
        data = path.read_bytes()[:TEXT_SAMPLE_SIZE]
    except OSError:
        return False

    if not data:
        return True
    if any(data.startswith(signature) for signature in BINARY_SIGNATURES):
        return False
    if b"\x00" in data:
        return False

    best_score = 10**9
    best_length = 0
    for encoding in TEXT_ENCODING_CANDIDATES:
        try:
            decoded = data.decode(encoding)
        except UnicodeDecodeError:
            continue
        best_score = min(best_score, mojibake_score(decoded))
        best_length = max(best_length, len(decoded))

    if best_length == 0:
        decoded = data.decode("utf-8", errors="replace")
        best_score = mojibake_score(decoded)
        best_length = len(decoded)

    return best_score / max(best_length, 1) <= MAX_TEXT_SCORE_RATIO


def wrap_line(line: str, max_width: float, fontname: str, fontsize: float) -> list[str]:
    line = line.expandtabs(4)
    if line == "":
        return [""]

    wrapped = []
    current = ""
    for char in line:
        candidate = current + char
        if current and fitz.get_text_length(candidate, fontname=fontname, fontsize=fontsize) > max_width:
            wrapped.append(current)
            current = char
        else:
            current = candidate
    wrapped.append(current)
    return wrapped


def text_to_wrapped_lines(text: str, max_width: float, fontname: str, fontsize: float) -> list[str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = []
    for line in normalized.split("\n"):
        lines.extend(wrap_line(line, max_width, fontname, fontsize))
    return lines or [""]


def write_text_pdf(text: str, output_path: Path) -> None:
    page_width = 595
    page_height = 842
    margin = 36
    fontname = "japan"
    fontsize = 10
    line_height = 14
    max_width = page_width - margin * 2
    bottom_limit = page_height - margin

    doc = fitz.open()
    page = doc.new_page(width=page_width, height=page_height)
    y = margin

    for line in text_to_wrapped_lines(text, max_width, fontname, fontsize):
        if y + line_height > bottom_limit:
            page = doc.new_page(width=page_width, height=page_height)
            y = margin
        page.insert_text((margin, y), line, fontsize=fontsize, fontname=fontname)
        y += line_height

    doc.save(output_path)
    doc.close()


def convert_text_to_pdf(text_path: str | Path, delete_source: bool = True) -> TextConversionResult:
    text_path = Path(text_path)
    output_path = unique_pdf_path(text_path)

    try:
        text = read_text_file(text_path)
        write_text_pdf(text, output_path)

        if delete_source:
            text_path.unlink(missing_ok=True)

        return TextConversionResult(success=True, source=text_path, output=output_path)
    except Exception as exc:
        return TextConversionResult(success=False, source=text_path, output=output_path, error=str(exc))


def convert_all_texts_to_pdf(folder_path: str | Path, issue_report=None) -> list[TextConversionResult]:
    folder_path = Path(folder_path)
    text_files = sorted(
        path
        for path in folder_path.rglob("*")
        if path.is_file() and is_probably_text_file(path)
    )

    results = []
    for text_file in text_files:
        print(f"Converting text file: {text_file}")
        result = convert_text_to_pdf(text_file)
        results.append(result)
        if result.success:
            print(f"Text conversion complete: {result.output}")
            continue

        message = f"テキストファイルのPDF変換に失敗しました: {result.source} -> {result.error}"
        print(message)
        if issue_report is not None:
            issue_report.append(
                {
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "category": "Text conversion error",
                    "message": message,
                }
            )

    return results
