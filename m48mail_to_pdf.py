from __future__ import annotations

import gc
import html
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime
from email import policy
from email.header import decode_header, make_header
from email.parser import BytesParser
from email.utils import getaddresses, parsedate_to_datetime
from pathlib import Path
from typing import Iterable

CID_PROPERTY_UNICODE = "http://schemas.microsoft.com/mapi/proptag/0x3712001F"
CID_PROPERTY_ANSI = "http://schemas.microsoft.com/mapi/proptag/0x3712001E"
MIME_TAG_PROPERTY = "http://schemas.microsoft.com/mapi/proptag/0x370E001F"
BODY_HTML_NAME = "本文.html"
BODY_PDF_NAME = "01本文.pdf"
INLINE_IMAGE_DIR_NAME = "本文画像"
ATTACHMENT_DIR_NAME = "02添付フォルダ"
MAIL_FILE_SUFFIXES = {".msg", ".eml"}


@dataclass(frozen=True)
class ExportResult:
    success: bool
    source: Path
    output: Path | None = None
    error: str = ""


def safe_file_name(name: str | None, max_length: int = 80) -> str:
    invalid = set('<>:"/\\|?*')
    safe = "".join("_" if char in invalid or ord(char) < 32 else char for char in (name or ""))
    safe = safe.strip().rstrip(".")
    if not safe:
        safe = "no_subject"
    if len(safe) > max_length:
        safe = safe[:max_length].strip().rstrip(".")
    return safe or "no_subject"


def unique_directory(parent: Path, name: str) -> Path:
    base_name = safe_file_name(name)
    path = parent / base_name
    index = 2
    while path.exists():
        path = parent / f"{base_name}_{index}"
        index += 1
    path.mkdir(parents=True)
    return path


def unique_file_path(directory: Path, file_name: str) -> Path:
    safe_name = safe_file_name(file_name, max_length=120)
    path = directory / safe_name
    stem = path.stem
    suffix = path.suffix
    index = 2
    while path.exists():
        path = directory / f"{stem}_{index}{suffix}"
        index += 1
    return path


def numbered_attachment_name(index: int, file_name: str) -> str:
    return f"{index:02d}_{file_name}"


def browser_executable_candidates() -> list[Path]:
    candidates = [
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
    ]
    return [candidate for candidate in candidates if candidate.exists()]


def convert_html_to_pdf(html_path: Path, pdf_path: Path) -> None:
    browsers = browser_executable_candidates()
    errors: list[str] = []

    for browser in browsers:
        with tempfile.TemporaryDirectory() as profile_dir:
            command = [
                str(browser),
                "--headless=new",
                "--disable-gpu",
                "--disable-gpu-compositing",
                "--disable-software-rasterizer",
                "--disable-3d-apis",
                "--disable-extensions",
                "--disable-dev-shm-usage",
                "--no-first-run",
                "--no-default-browser-check",
                "--allow-file-access-from-files",
                f"--user-data-dir={profile_dir}",
                f"--print-to-pdf={pdf_path}",
                html_path.resolve().as_uri(),
            ]
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=60,
            )
        if result.returncode == 0 and pdf_path.exists() and pdf_path.stat().st_size > 0:
            return
        message = (result.stderr or "").strip() or (result.stdout or "").strip() or "PDF変換に失敗しました。"
        errors.append(f"{browser}: {message}")

    if not errors:
        errors.append("メール本文をPDF化するには Microsoft Edge または Google Chrome が必要です。")
    raise RuntimeError("\n".join(errors))


def write_body_pdf_and_cleanup(mail_dir: Path, html_body: str, inline_dir: Path) -> None:
    html_path = mail_dir / BODY_HTML_NAME
    pdf_path = mail_dir / BODY_PDF_NAME
    html_path.write_text(html_body, encoding="utf-8")
    convert_html_to_pdf(html_path, pdf_path)
    html_path.unlink(missing_ok=True)
    if inline_dir.exists():
        shutil.rmtree(inline_dir)


def get_attachment_property(attachment, prop: str):
    try:
        return attachment.PropertyAccessor.GetProperty(prop)
    except Exception:
        return None


def is_inline_attachment(attachment, html_body: str | None) -> bool:
    content_id = get_content_id(attachment)
    mime_tag = get_attachment_property(attachment, MIME_TAG_PROPERTY)
    is_image_mime = isinstance(mime_tag, str) and mime_tag.lower().startswith("image/")

    if not content_id or not html_body:
        return False

    cid = content_id.strip("<>")
    has_cid_reference = f"cid:{cid}".lower() in html_body.lower()
    return is_image_mime and has_cid_reference


def get_content_id(attachment) -> str | None:
    content_id = get_attachment_property(attachment, CID_PROPERTY_UNICODE)
    if not content_id:
        content_id = get_attachment_property(attachment, CID_PROPERTY_ANSI)
    return str(content_id) if content_id else None


def format_attachment_names(attachment_names: Iterable[str]) -> str:
    return " / ".join(name for name in attachment_names if name)


def mail_info_lines(mail_item, attachment_names: Iterable[str] = ()) -> list[str]:
    return [
        f"件名: {getattr(mail_item, 'Subject', '')}",
        f"差出人: {getattr(mail_item, 'SenderName', '')} <{getattr(mail_item, 'SenderEmailAddress', '')}>",
        f"宛先: {getattr(mail_item, 'To', '')}",
        f"CC: {getattr(mail_item, 'CC', '')}",
        f"添付ファイル: {format_attachment_names(attachment_names)}",
        f"受信日時: {getattr(mail_item, 'ReceivedTime', '')}",
        f"送信日時: {getattr(mail_item, 'SentOn', '')}",
    ]


def decode_mime_text(value: str | None) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value


def format_addresses(value: str | None) -> str:
    addresses = []
    for name, address in getaddresses([value or ""]):
        decoded_name = decode_mime_text(name)
        if decoded_name and address:
            addresses.append(f"{decoded_name} <{address}>")
        elif address:
            addresses.append(address)
        elif decoded_name:
            addresses.append(decoded_name)
    return ", ".join(addresses)


def eml_info_lines(message, attachment_names: Iterable[str] = ()) -> list[str]:
    return [
        f"件名: {decode_mime_text(message.get('Subject'))}",
        f"差出人: {format_addresses(message.get('From'))}",
        f"宛先: {format_addresses(message.get('To'))}",
        f"CC: {format_addresses(message.get('Cc'))}",
        f"添付ファイル: {format_attachment_names(attachment_names)}",
        f"受信日時: {decode_mime_text(message.get('Date'))}",
        "送信日時: ",
    ]


def decode_part_text(part, preferred_encoding: str = "auto") -> str:
    payload = part.get_payload(decode=True)
    if payload is None:
        try:
            return part.get_content()
        except Exception:
            return ""

    explicit_candidates = unique_texts(
        [
            None if preferred_encoding == "auto" else preferred_encoding,
            part.get_content_charset(),
            *extract_declared_charsets(payload),
        ]
    )
    for candidate in explicit_candidates:
        try:
            return payload.decode(candidate)
        except (LookupError, UnicodeDecodeError):
            continue

    utf16_candidates = ["utf-16", "utf-16le", "utf-16be"] if looks_like_utf16(payload) else []
    candidates = unique_texts(
        [
            "utf-8-sig",
            "utf-8",
            "cp932",
            "shift_jis",
            "iso-2022-jp",
            "euc-jp",
            *utf16_candidates,
        ]
    )

    best_text = ""
    best_score = -10**9
    for candidate in candidates:
        try:
            text = payload.decode(candidate)
        except (LookupError, UnicodeDecodeError):
            continue
        score = score_decoded_text(text)
        if score > best_score:
            best_text = text
            best_score = score

    if best_text:
        return best_text

    for candidate in candidates:
        try:
            text = payload.decode(candidate, errors="replace")
        except LookupError:
            continue
        score = score_decoded_text(text)
        if score > best_score:
            best_text = text
            best_score = score
    return best_text


def extract_declared_charsets(payload: bytes) -> list[str]:
    head = payload[:4096].decode("ascii", errors="ignore")
    return re.findall(r"charset\s*=\s*[\"']?([A-Za-z0-9._-]+)", head, flags=re.IGNORECASE)


def looks_like_utf16(payload: bytes) -> bool:
    if payload.startswith((b"\xff\xfe", b"\xfe\xff")):
        return True

    sample = payload[:512]
    if len(sample) < 4:
        return False

    even_nuls = sample[0::2].count(0)
    odd_nuls = sample[1::2].count(0)
    pair_count = max(1, len(sample) // 2)
    return even_nuls / pair_count > 0.25 or odd_nuls / pair_count > 0.25


def unique_texts(values: Iterable[str | None]) -> list[str]:
    result = []
    seen = set()
    for value in values:
        if not value:
            continue
        key = value.lower()
        if key not in seen:
            result.append(value)
            seen.add(key)
    return result


def normalize_html_charset(html_body: str) -> str:
    if re.search(r"<meta[^>]+charset\s*=", html_body, flags=re.IGNORECASE):
        return re.sub(
            r"<meta[^>]+charset\s*=\s*[\"']?[^\"'\s/>;]+[^>]*>",
            '<meta charset="utf-8">',
            html_body,
            count=1,
            flags=re.IGNORECASE,
        )
    if re.search(r"<head[^>]*>", html_body, flags=re.IGNORECASE):
        return re.sub(
            r"(<head[^>]*>)",
            r'\1<meta charset="utf-8">',
            html_body,
            count=1,
            flags=re.IGNORECASE,
        )
    return f'<html><head><meta charset="utf-8"></head><body>{html_body}</body></html>'


def prepend_mail_info(html_body: str, lines: Iterable[str]) -> str:
    info_html = build_mail_info_html(lines)
    if re.search(r"<body\b[^>]*>", html_body, flags=re.IGNORECASE):
        return re.sub(
            r"(<body\b[^>]*>)",
            r"\1" + info_html,
            html_body,
            count=1,
            flags=re.IGNORECASE,
        )
    return f'<html><head><meta charset="utf-8"></head><body>{info_html}{html_body}</body></html>'


def build_mail_info_html(lines: Iterable[str]) -> str:
    rows = []
    for line in lines:
        label, separator, value = line.partition(":")
        if separator:
            rows.append(
                "<tr>"
                f"<th>{html.escape(label)}</th>"
                f"<td>{html.escape(value.strip())}</td>"
                "</tr>"
            )
        else:
            rows.append(f'<tr><td colspan="2">{html.escape(line)}</td></tr>')
    return (
        '<section style="border:1px solid #d0d7de;'
        'padding:12px;margin:0 0 16px 0;'
        'font-family:Meiryo, sans-serif;font-size:14px;">'
        '<table style="border-collapse:collapse;">'
        + "".join(rows)
        + "</table></section>"
    )


def score_decoded_text(text: str) -> int:
    replacement_count = text.count("\ufffd")
    mojibake_count = sum(text.count(token) for token in ("縺", "繧", "譁", "莨", "蜷", "荳", "髮"))
    control_count = sum(1 for char in text if ord(char) < 32 and char not in "\r\n\t")
    japanese_count = sum(
        1
        for char in text
        if "\u3040" <= char <= "\u30ff" or "\u4e00" <= char <= "\u9fff"
    )
    ascii_count = sum(1 for char in text if " " <= char <= "~")
    return japanese_count * 3 + ascii_count - replacement_count * 100 - mojibake_count * 20 - control_count * 20


def make_html_body(mail_item) -> str:
    html_body = getattr(mail_item, "HTMLBody", "") or ""
    if html_body.strip():
        return normalize_html_charset(html_body)

    plain_text = html.escape(getattr(mail_item, "Body", "") or "")
    return f'<html><head><meta charset="utf-8"></head><body><pre>{plain_text}</pre></body></html>'


def date_prefix(mail_item) -> str:
    try:
        received_time = getattr(mail_item, "ReceivedTime", None)
        if not received_time:
            return ""
        if hasattr(received_time, "strftime"):
            return received_time.strftime("%Y%m%d_%H%M%S_")
        if isinstance(received_time, datetime):
            value = received_time
        else:
            value = datetime.fromisoformat(str(received_time))
        return value.strftime("%Y%m%d_%H%M%S_")
    except Exception:
        return ""


def replace_cid_reference(html_body: str, content_id: str, relative_path: str) -> str:
    cid = re.escape(content_id.strip("<>"))
    return re.sub(f"cid:{cid}", relative_path, html_body, flags=re.IGNORECASE)


def eml_date_prefix(message) -> str:
    try:
        date_value = parsedate_to_datetime(message.get("Date"))
        return date_value.strftime("%Y%m%d_%H%M%S_")
    except Exception:
        return ""


def get_eml_body(message, preferred_encoding: str = "auto") -> str:
    html_part = None
    plain_part = None

    for part in message.walk():
        if part.is_multipart():
            continue
        content_type = part.get_content_type()
        disposition = (part.get_content_disposition() or "").lower()
        if disposition == "attachment":
            continue
        if content_type == "text/html" and html_part is None:
            html_part = part
        elif content_type == "text/plain" and plain_part is None:
            plain_part = part

    if html_part is not None:
        return normalize_html_charset(decode_part_text(html_part, preferred_encoding))
    if plain_part is not None:
        plain_text = html.escape(decode_part_text(plain_part, preferred_encoding))
        return f'<html><head><meta charset="utf-8"></head><body><pre>{plain_text}</pre></body></html>'
    return '<html><head><meta charset="utf-8"></head><body></body></html>'


def eml_file_name(part, fallback: str) -> str:
    file_name = part.get_filename()
    if file_name:
        return decode_mime_text(file_name)
    content_type = part.get_content_type()
    extension = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "image/bmp": ".bmp",
        "image/webp": ".webp",
    }.get(content_type, "")
    return fallback + extension


def export_eml_file(eml_path: str | Path, work_root: str | Path, eml_encoding: str = "auto") -> ExportResult:
    eml_path = Path(eml_path)
    work_root = Path(work_root)

    try:
        with eml_path.open("rb") as file:
            message = BytesParser(policy=policy.default).parse(file)

        subject = decode_mime_text(message.get("Subject")) or eml_path.stem
        mail_dir = unique_directory(work_root, eml_date_prefix(message) + subject)
        inline_dir = mail_dir / INLINE_IMAGE_DIR_NAME
        attach_dir = mail_dir / ATTACHMENT_DIR_NAME
        inline_dir.mkdir()
        attach_dir.mkdir()

        html_body = get_eml_body(message, eml_encoding)
        attachment_index = 1
        attachment_names = []

        for part in message.walk():
            if part.is_multipart():
                continue
            content_type = part.get_content_type()
            disposition = (part.get_content_disposition() or "").lower()
            if content_type in {"text/plain", "text/html"} and disposition != "attachment":
                continue

            payload = part.get_payload(decode=True)
            if payload is None:
                continue

            content_id = part.get("Content-ID")
            is_inline_image = (
                content_id
                and content_type.lower().startswith("image/")
                and f"cid:{content_id.strip('<>')}".lower() in html_body.lower()
                and disposition != "attachment"
            )

            file_name = eml_file_name(part, f"attachment_{attachment_index}")
            if is_inline_image:
                save_path = unique_file_path(inline_dir, file_name)
                save_path.write_bytes(payload)
                relative_path = f"{INLINE_IMAGE_DIR_NAME}/{save_path.name}"
                html_body = replace_cid_reference(html_body, content_id, relative_path)
            else:
                save_path = unique_file_path(attach_dir, numbered_attachment_name(attachment_index, file_name))
                save_path.write_bytes(payload)
                attachment_names.append(save_path.name)
                attachment_index += 1

        html_body = prepend_mail_info(html_body, eml_info_lines(message, attachment_names))
        write_body_pdf_and_cleanup(mail_dir, html_body, inline_dir)
        return ExportResult(success=True, source=eml_path, output=mail_dir)
    except Exception as exc:
        return ExportResult(success=False, source=eml_path, error=str(exc))


def export_msg_file(msg_path: str | Path, work_root: str | Path, outlook) -> ExportResult:
    msg_path = Path(msg_path)
    work_root = Path(work_root)
    item = None

    try:
        item = outlook.Session.OpenSharedItem(str(msg_path))
        subject = getattr(item, "Subject", None) or msg_path.stem

        mail_dir = unique_directory(work_root, date_prefix(item) + subject)
        inline_dir = mail_dir / INLINE_IMAGE_DIR_NAME
        attach_dir = mail_dir / ATTACHMENT_DIR_NAME
        inline_dir.mkdir()
        attach_dir.mkdir()

        html_body = make_html_body(item)
        attachment_count = int(item.Attachments.Count)
        attachment_index = 1
        attachment_names = []

        for index in range(1, attachment_count + 1):
            attachment = None
            try:
                attachment = item.Attachments.Item(index)
                file_name = getattr(attachment, "FileName", None) or f"attachment_{index}"

                if is_inline_attachment(attachment, html_body):
                    save_path = unique_file_path(inline_dir, file_name)
                    attachment.SaveAsFile(str(save_path))
                    content_id = get_content_id(attachment)
                    if content_id:
                        relative_path = f"{INLINE_IMAGE_DIR_NAME}/{save_path.name}"
                        html_body = replace_cid_reference(html_body, content_id, relative_path)
                else:
                    save_path = unique_file_path(attach_dir, numbered_attachment_name(attachment_index, file_name))
                    attachment.SaveAsFile(str(save_path))
                    attachment_names.append(save_path.name)
                    attachment_index += 1
            finally:
                if attachment is not None:
                    release_com_object(attachment)

        html_body = prepend_mail_info(html_body, mail_info_lines(item, attachment_names))
        write_body_pdf_and_cleanup(mail_dir, html_body, inline_dir)

        close_mail_item(item)
        item = None
        return ExportResult(success=True, source=msg_path, output=mail_dir)
    except Exception as exc:
        return ExportResult(success=False, source=msg_path, error=str(exc))
    finally:
        if item is not None:
            release_com_object(item)


def export_mail_file(mail_path: str | Path, work_root: str | Path, outlook=None, eml_encoding: str = "auto") -> ExportResult:
    mail_path = Path(mail_path)
    work_root = Path(work_root)
    mailbox_extension = mail_path.suffix.lower()

    if mailbox_extension == ".msg":
        if outlook is None:
            outlook = create_outlook_application()
        return export_msg_file(mail_path, work_root, outlook)
    if mailbox_extension == ".eml":
        return export_eml_file(mail_path, work_root, eml_encoding)
    return ExportResult(success=False, source=mail_path, error=f"対応していないメール形式です: {mail_path.suffix}")


def create_outlook_application():
    try:
        import pythoncom
        import win32timezone  # noqa: F401 - needed by pywin32 COM date conversion in packaged builds.
        import win32com.client
    except ImportError as exc:
        raise RuntimeError("pywin32 が必要です。`pip install pywin32` を実行してください。") from exc

    pythoncom.CoInitialize()
    try:
        return win32com.client.Dispatch("Outlook.Application")
    except Exception as exc:
        pythoncom.CoUninitialize()
        raise RuntimeError(
            ".msgファイルをPDF化するには Microsoft Outlook が必要です。"
            "OutlookがこのPCにインストールされ、通常起動できる状態か確認してください。"
            f" 詳細: {exc}"
        ) from exc


def release_com_object(obj) -> None:
    try:
        del obj
    except Exception:
        pass
    gc.collect()


def close_mail_item(item) -> None:
    try:
        item.Close(1)
    except Exception:
        pass
    release_com_object(item)


def uninitialize_com() -> None:
    try:
        import pythoncom
        pythoncom.CoUninitialize()
    except Exception:
        pass


def expand_mail_files_in_folder(
    source_folder: str | Path,
    destination_folder: str | Path,
    recursive: bool = True,
    eml_encoding: str = "auto",
) -> list[ExportResult]:
    source_folder = Path(source_folder)
    destination_folder = Path(destination_folder)

    if not source_folder.exists():
        raise FileNotFoundError(f"メール検索元フォルダが見つかりません: {source_folder}")

    if not destination_folder.exists():
        destination_folder.mkdir(parents=True)

    files = sorted(
        [path for path in source_folder.rglob("*") if path.is_file() and path.suffix.lower() in MAIL_FILE_SUFFIXES]
    ) if recursive else sorted(
        [path for path in source_folder.iterdir() if path.is_file() and path.suffix.lower() in MAIL_FILE_SUFFIXES]
    )

    outreach = create_outlook_application() if any(path.suffix.lower() == ".msg" for path in files) else None
    results = []
    try:
        for mail_file in files:
            try:
                relative_parent = mail_file.parent.relative_to(source_folder)
            except ValueError:
                relative_parent = Path()
            mail_destination = destination_folder / relative_parent
            mail_destination.mkdir(parents=True, exist_ok=True)
            result = export_mail_file(mail_file, mail_destination, outlook=outreach, eml_encoding=eml_encoding)
            results.append(result)
    finally:
        if outreach is not None:
            release_com_object(outreach)
            uninitialize_com()
    return results


def expand_mail_file(mail_path: str | Path, destination_folder: str | Path, outlook=None, eml_encoding: str = "auto") -> ExportResult:
    return export_mail_file(mail_path, destination_folder, outlook=outlook, eml_encoding=eml_encoding)
