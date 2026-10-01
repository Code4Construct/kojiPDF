from __future__ import annotations

import gc
import html
import gzip
import io
import os
import re
import shutil
import time
from dataclasses import dataclass
from datetime import datetime
from email import policy
from email.header import decode_header, make_header
from email.parser import BytesParser
from email.utils import getaddresses, parsedate_to_datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Iterable
from uuid import uuid4
from urllib.parse import quote, unquote
import m53path_display_map as display_names

CID_PROPERTY_UNICODE = "http://schemas.microsoft.com/mapi/proptag/0x3712001F"
CID_PROPERTY_ANSI = "http://schemas.microsoft.com/mapi/proptag/0x3712001E"
MIME_TAG_PROPERTY = "http://schemas.microsoft.com/mapi/proptag/0x370E001F"
BODY_HTML_NAME = "本文.html"
BODY_PDF_NAME = "01本文.pdf"
INLINE_IMAGE_DIR_NAME = "本文画像"
ATTACHMENT_DIR_NAME = "02添付フォルダ"
MAIL_FILE_SUFFIXES = {".msg", ".eml"}
OFFICE_COM_RETRY_DELAYS = (3, 8, 15)
OFFICE_COM_STARTUP_WAIT_SECONDS = 2
MAIL_EXPORT_COOLDOWN_SECONDS = 1
WORD_DO_NOT_SAVE_CHANGES = 0
MAIL_BODY_CLEANUP_RETRY_DELAYS = (0.5, 1, 2, 5)
EMZ_EXTENSION = ".emz"
TRANSIENT_COM_HRESULTS = {
    -2147418111,  # Call was rejected by callee.
    -2147417846,  # Application is busy.
    -2147023170,  # RPC server unavailable.
}
SIGNATURE_ATTACHMENT_NAMES = {
    "smime.p7s",
    "signature.p7s",
    "signeddata.p7s",
}
SIGNATURE_MIME_TYPES = {
    "application/pkcs7-signature",
    "application/x-pkcs7-signature",
    "multipart/signed",
}
UNKNOWN_MAIL_SENDER = "unknown_sender"


def contains_malformed_unicode(value) -> bool:
    text = str(value or "")
    if any(0xD800 <= ord(char) <= 0xDFFF for char in text):
        return True
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        return True
    return False


def safe_text_for_utf8(value, context="") -> str:
    text = str(value or "")
    if not contains_malformed_unicode(text):
        return text

    cleaned = "".join("\ufffd" if 0xD800 <= ord(char) <= 0xDFFF else char for char in text)
    return cleaned.encode("utf-8", errors="replace").decode("utf-8", errors="replace")


def make_encoding_issue(context, original, cleaned):
    if str(original or "") == str(cleaned or ""):
        return None
    return {
        "category": "Mail encoding issue",
        "message": (
            f"Mail text contained malformed Unicode and was sanitized before UTF-8 output. "
            f"Context: {safe_text_for_utf8(context)}"
        ),
    }


def append_encoding_issue(warnings, context, original, cleaned):
    issue = make_encoding_issue(context, original, cleaned)
    if issue is not None:
        warnings.append(issue)


@dataclass(frozen=True)
class ExportResult:
    success: bool
    source: Path
    output: Path | None = None
    error: str = ""
    warnings: tuple[dict[str, str], ...] = ()


def safe_file_name(name: str | None, max_length: int = 80) -> str:
    invalid = set('<>:"/\\|?*')
    source = safe_text_for_utf8(name)
    safe = "".join("_" if char in invalid or ord(char) < 32 else char for char in source)
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


def unique_attachment_path(directory: Path, file_name: str) -> Path:
    root = display_names.find_map_root(directory)
    if root is None:
        return unique_file_path(directory, file_name)
    suffix = Path(file_name).suffix
    return display_names.unique_short_file_path(directory, "a", suffix, file_name)


def unique_inline_path(directory: Path, file_name: str) -> Path:
    root = display_names.find_map_root(directory)
    if root is None:
        return unique_file_path(directory, file_name)
    suffix = Path(file_name).suffix
    return display_names.unique_short_file_path(directory, "i", suffix, file_name)


def unique_mail_directory(parent: Path, display_name: str) -> Path:
    root = display_names.find_map_root(parent)
    if root is None:
        return unique_directory(parent, display_name)
    return display_names.unique_short_directory(parent, "m", display_name)


def unique_named_directory(parent: Path, display_name: str, prefix: str) -> Path:
    root = display_names.find_map_root(parent)
    if root is None:
        return unique_directory(parent, display_name)
    return display_names.unique_short_directory(parent, prefix, display_name)


def numbered_attachment_name(index: int, file_name: str) -> str:
    return f"{index:02d}_{file_name}"


def exception_values(exc: BaseException):
    values = []

    def collect(value):
        values.append(value)
        if isinstance(value, (tuple, list)):
            for item in value:
                collect(item)

    collect(getattr(exc, "args", ()))
    return values


def is_transient_com_error(exc: BaseException) -> bool:
    return any(isinstance(value, int) and value in TRANSIENT_COM_HRESULTS for value in exception_values(exc))


def run_with_com_retry(operation, label: str):
    for delay in (*OFFICE_COM_RETRY_DELAYS, None):
        try:
            return operation()
        except Exception as exc:
            if delay is None or not is_transient_com_error(exc):
                raise
            print(f"{label} is busy. Retrying in {delay} seconds: {exc}")
            time.sleep(delay)



def close_word_document_without_saving(document) -> None:
    try:
        document.Saved = True
    except Exception:
        pass
    try:
        document.Close(SaveChanges=WORD_DO_NOT_SAVE_CHANGES)
    except TypeError:
        try:
            document.Close(False)
        except Exception:
            pass
    except Exception:
        pass


def quit_word_without_saving(word) -> None:
    try:
        word.DisplayAlerts = 0
    except Exception:
        pass
    try:
        word.NormalTemplate.Saved = True
    except Exception:
        pass
    try:
        word.Quit(SaveChanges=WORD_DO_NOT_SAVE_CHANGES)
    except TypeError:
        try:
            word.Quit()
        except Exception:
            pass
    except Exception:
        pass
FILE_HREF_RE = re.compile(
    r"(<a\b[^>]*?\bhref\s*=\s*)([\"'])(.*?)\2",
    re.IGNORECASE | re.DOTALL,
)
LINK_MARKER_PREFIX = "https://kojipdf.invalid/link/"


def replace_file_hrefs_with_markers(html_body: str):
    """Give each file link an unambiguous target for Word's PDF export."""
    original_by_marker = {}

    def replace(match):
        original = html.unescape(match.group(3))
        if not original.lower().startswith("file:"):
            return match.group(0)
        marker = LINK_MARKER_PREFIX + uuid4().hex
        original_by_marker[marker] = original
        return match.group(1) + match.group(2) + marker + match.group(2)

    return FILE_HREF_RE.sub(replace, html_body), original_by_marker


def restore_original_file_links(pdf_path: Path, original_by_marker: dict[str, str]) -> None:
    if not original_by_marker:
        return

    import fitz

    doc = fitz.open(pdf_path)
    replacement = pdf_path.with_name(pdf_path.stem + "_links.tmp.pdf")
    found = set()
    try:
        for page in doc:
            for link in list(page.get_links()):
                marker = link.get("uri")
                if marker not in original_by_marker:
                    continue
                page.delete_link(link)
                page.insert_link({
                    "kind": fitz.LINK_URI,
                    "from": link["from"],
                    "uri": original_by_marker[marker],
                })
                found.add(marker)

        missing = original_by_marker.keys() - found
        if missing:
            raise RuntimeError(
                f"Word PDF export lost {len(missing)} file hyperlink(s); "
                "the mail body PDF was not accepted."
            )
        doc.save(replacement)
        doc.close()
        os.replace(replacement, pdf_path)
    finally:
        if not doc.is_closed:
            doc.close()
        replacement.unlink(missing_ok=True)


def convert_html_to_pdf(html_path: Path, pdf_path: Path) -> None:
    try:
        import win32com.client
    except ImportError as exc:
        raise RuntimeError("Microsoft Word and pywin32 are required to convert mail body HTML to PDF.") from exc

    word = None
    document = None
    try:
        word = run_with_com_retry(lambda: win32com.client.DispatchEx("Word.Application"), "Microsoft Word")
        word.Visible = False
        word.DisplayAlerts = 0
        try:
            word.Options.SaveNormalPrompt = False
        except Exception:
            pass
        try:
            word.NormalTemplate.Saved = True
        except Exception:
            pass
        time.sleep(OFFICE_COM_STARTUP_WAIT_SECONDS)
        document = run_with_com_retry(
            lambda: word.Documents.Open(
                FileName=str(html_path.resolve()),
                ConfirmConversions=False,
                ReadOnly=True,
                AddToRecentFiles=False,
                NoEncodingDialog=True,
                Visible=False,
            ),
            "Microsoft Word",
        )
        optimize_word_mail_layout(document)
        run_with_com_retry(lambda: document.ExportAsFixedFormat(str(pdf_path.resolve()), 17), "Microsoft Word")
        try:
            document.Saved = True
        except Exception:
            pass
    except Exception as exc:
        raise RuntimeError(
            "Microsoft Word mail body PDF conversion failed for "
            f"{html_path}: {type(exc).__name__}: {exc}"
        ) from exc
    finally:
        if document is not None:
            close_word_document_without_saving(document)
            release_com_object(document)
            document = None
        if word is not None:
            quit_word_without_saving(word)
            release_com_object(word)
            word = None

    if not pdf_path.exists() or pdf_path.stat().st_size <= 0:
        raise RuntimeError(
            "Microsoft Word mail body PDF conversion did not create a readable PDF: "
            f"{pdf_path}"
        )

def optimize_word_mail_layout(document) -> None:
    try:
        for section in document.Sections:
            section.PageSetup.TopMargin = 36
            section.PageSetup.BottomMargin = 36
            section.PageSetup.LeftMargin = 36
            section.PageSetup.RightMargin = 36
    except Exception:
        pass

    try:
        if document.Tables.Count >= 1:
            table = document.Tables.Item(1)
            table.AllowAutoFit = False
            table.AutoFitBehavior(0)
            table.Columns.Item(1).PreferredWidth = 84
    except Exception:
        pass



def unlink_mail_body_source_with_retry(html_path: Path) -> None:
    last_error = None
    for delay in (0, *MAIL_BODY_CLEANUP_RETRY_DELAYS):
        if delay:
            time.sleep(delay)
        try:
            html_path.unlink(missing_ok=True)
            return
        except (PermissionError, OSError) as exc:
            last_error = exc
    print(f"Mail body HTML cleanup skipped because the file is still in use: {html_path} -> {last_error}")
def cleanup_mail_body_sources(html_path: Path, inline_dir: Path) -> None:
    unlink_mail_body_source_with_retry(html_path)

    if inline_dir.exists():
        try:
            shutil.rmtree(inline_dir)
        except (PermissionError, OSError) as exc:
            print(f"メール本文画像フォルダの削除をスキップしました（使用中）: {inline_dir} -> {exc}")


def write_body_pdf_and_cleanup(
    mail_dir: Path,
    html_body: str,
    inline_dir: Path,
    warnings=None,
    context="mail body",
) -> None:
    warnings = warnings if warnings is not None else []
    html_path = mail_dir / BODY_HTML_NAME
    pdf_path = mail_dir / BODY_PDF_NAME
    html_body = prefer_non_vml_image_fallbacks(html_body)
    html_body = flatten_absolute_image_overlays(html_body, mail_dir, warnings, context)
    safe_html_body = safe_text_for_utf8(html_body, context)
    append_encoding_issue(warnings, context, html_body, safe_html_body)
    word_html, original_by_marker = replace_file_hrefs_with_markers(safe_html_body)
    html_path.write_text(word_html, encoding="utf-8")
    convert_html_to_pdf(html_path, pdf_path)
    restore_original_file_links(pdf_path, original_by_marker)
    cleanup_mail_body_sources(html_path, inline_dir)


def get_attachment_property(attachment, prop: str):
    try:
        return attachment.PropertyAccessor.GetProperty(prop)
    except Exception:
        return None


def is_emz_file(file_name: str | None) -> bool:
    return Path(str(file_name or "")).suffix.lower() == EMZ_EXTENSION


def html_references_cid(html_body: str | None, content_id: str | None) -> bool:
    if not content_id or not html_body:
        return False
    cid = content_id.strip("<>")
    return f"cid:{cid}".lower() in html_body.lower()


def is_inline_attachment(attachment, html_body: str | None) -> bool:
    content_id = get_content_id(attachment)
    mime_tag = get_attachment_property(attachment, MIME_TAG_PROPERTY)
    is_image_mime = isinstance(mime_tag, str) and mime_tag.lower().startswith("image/")

    file_name = getattr(attachment, "FileName", None)
    return (is_image_mime or is_emz_file(file_name)) and html_references_cid(html_body, content_id)


def get_content_id(attachment) -> str | None:
    content_id = get_attachment_property(attachment, CID_PROPERTY_UNICODE)
    if not content_id:
        content_id = get_attachment_property(attachment, CID_PROPERTY_ANSI)
    return str(content_id) if content_id else None


def convert_emz_payload_to_png(payload: bytes, output_path: Path) -> None:
    from PIL import Image

    emf_payload = gzip.decompress(payload)
    with Image.open(io.BytesIO(emf_payload)) as image:
        image.load(dpi=144)
        image.save(output_path, format="PNG")


def make_emz_conversion_issue(context: str, error: Exception):
    return {
        "category": "EMZ conversion error",
        "message": f"EMZ inline image conversion failed: {context} -> {error}",
    }


def save_inline_payload(payload, inline_dir, file_name, warnings, context):
    if not is_emz_file(file_name):
        save_path = unique_inline_path(inline_dir, file_name)
        save_path.write_bytes(payload)
        return save_path

    save_path = unique_inline_path(inline_dir, Path(file_name).with_suffix(".png").name)
    try:
        convert_emz_payload_to_png(payload, save_path)
        return save_path
    except Exception as exc:
        warnings.append(make_emz_conversion_issue(context, exc))
        save_path.unlink(missing_ok=True)
        return None


def save_outlook_inline_attachment(attachment, inline_dir, file_name, warnings, context):
    save_path = unique_inline_path(inline_dir, file_name)
    run_with_com_retry(lambda: attachment.SaveAsFile(str(save_path)), "Microsoft Outlook")
    if not is_emz_file(file_name):
        return save_path

    png_path = unique_inline_path(inline_dir, Path(file_name).with_suffix(".png").name)
    try:
        convert_emz_payload_to_png(save_path.read_bytes(), png_path)
        return png_path
    except Exception as exc:
        warnings.append(make_emz_conversion_issue(context, exc))
        png_path.unlink(missing_ok=True)
        return None
    finally:
        save_path.unlink(missing_ok=True)


def format_attachment_names(attachment_names: Iterable[str]) -> str:
    return " / ".join(name for name in attachment_names if name)


def mail_item_sender_smtp_address(mail_item) -> str:
    raw_address = str(getattr(mail_item, "SenderEmailAddress", "") or "").strip()
    if str(getattr(mail_item, "SenderEmailType", "") or "").upper() != "EX":
        return raw_address

    try:
        sender = mail_item.Sender
    except Exception:
        sender = None
    if sender is not None:
        try:
            exchange_user = sender.GetExchangeUser()
            smtp_address = str(getattr(exchange_user, "PrimarySmtpAddress", "") or "").strip()
            if smtp_address:
                return smtp_address
        except Exception:
            pass
        try:
            smtp_address = str(sender.PropertyAccessor.GetProperty(
                "http://schemas.microsoft.com/mapi/proptag/0x39FE001E"
            ) or "").strip()
            if smtp_address:
                return smtp_address
        except Exception:
            pass

    return raw_address if "@" in raw_address else ""


def outlook_recipients(mail_item, recipient_type: int) -> list[tuple[str, str]]:
    try:
        recipients = mail_item.Recipients
        count = int(recipients.Count)
    except Exception:
        return []

    result = []
    smtp_property = "http://schemas.microsoft.com/mapi/proptag/0x39FE001E"
    for index in range(1, count + 1):
        try:
            recipient = recipients.Item(index)
            if int(recipient.Type) != recipient_type:
                continue
            name = str(getattr(recipient, "Name", "") or "").strip()
            address = ""
            try:
                address = str(recipient.PropertyAccessor.GetProperty(smtp_property) or "").strip()
            except Exception:
                pass
            if not address:
                try:
                    entry = recipient.AddressEntry
                    user = entry.GetExchangeUser()
                    address = str(getattr(user, "PrimarySmtpAddress", "") or "").strip()
                    if not address:
                        group = entry.GetExchangeDistributionList()
                        address = str(getattr(group, "PrimarySmtpAddress", "") or "").strip()
                    if not address:
                        address = str(getattr(entry, "Address", "") or "").strip()
                except Exception:
                    pass
            if not address:
                address = str(getattr(recipient, "Address", "") or "").strip()
            result.append((name, address if "@" in address else ""))
        except Exception:
            continue
    return result


def outlook_to_recipients(mail_item) -> list[tuple[str, str]]:
    return outlook_recipients(mail_item, 1)  # Outlook olTo


def outlook_cc_recipients(mail_item) -> list[tuple[str, str]]:
    return outlook_recipients(mail_item, 2)  # Outlook olCC


def parsed_to_recipients(value: str | None) -> list[tuple[str, str]]:
    result = []
    for name, address in getaddresses([value or ""]):
        name = decode_mime_text(name).strip()
        address = address.strip()
        if name or address:
            result.append((name, address if "@" in address else ""))
    return result


def recipient_links_html(recipients: Iterable[tuple[str, str]]) -> str:
    entries = []
    for name, address in recipients:
        label = html.escape(name)
        if address:
            href = "mailto:" + quote(address, safe="@.+-_")
            entries.append(
                f'<a href="{html.escape(href, quote=True)}">'
                f'{label or html.escape(address)}</a>'
            )
        elif label:
            entries.append(label)
    return ", ".join(entries)


def mail_info_lines(mail_item, attachment_names: Iterable[str] = ()) -> list[str]:
    sender_name = str(getattr(mail_item, "SenderName", "") or "")
    sender_address = mail_item_sender_smtp_address(mail_item)
    sender_display = f"{sender_name} <{sender_address}>" if sender_address else sender_name
    return [
        f"件名: {getattr(mail_item, 'Subject', '')}",
        f"差出人: {sender_display}",
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


def first_address_display(value: str | None) -> str:
    for name, address in getaddresses([value or ""]):
        decoded_name = decode_mime_text(name).strip()
        if decoded_name:
            return decoded_name
        if address:
            return address.strip()
    return ""


def eml_sender_display(message) -> str:
    return first_address_display(message.get("From"))


def mail_item_sender_display(mail_item) -> str:
    sender_name = str(getattr(mail_item, "SenderName", "") or "").strip()
    if sender_name:
        return sender_name
    return str(getattr(mail_item, "SenderEmailAddress", "") or "").strip()

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


def prepend_mail_info(html_body: str, lines: Iterable[str], to_recipients=(), cc_recipients=()) -> str:
    info_html = build_mail_info_html(lines, to_recipients, cc_recipients)
    if re.search(r"<body\b[^>]*>", html_body, flags=re.IGNORECASE):
        return re.sub(
            r"(<body\b[^>]*>)",
            r"\1" + info_html,
            html_body,
            count=1,
            flags=re.IGNORECASE,
        )
    return f'<html><head><meta charset="utf-8"></head><body>{info_html}{html_body}</body></html>'


def build_mail_info_html(lines: Iterable[str], to_recipients=(), cc_recipients=()) -> str:
    rows = []
    to_html = recipient_links_html(to_recipients)
    cc_html = recipient_links_html(cc_recipients)
    for index, line in enumerate(lines):
        line = safe_text_for_utf8(line, "mail info line")
        label, separator, value = line.partition(":")
        if separator:
            display_value = html.escape(value.strip())
            if index == 2 and to_html:
                display_value = to_html
            elif index == 3 and cc_html:
                display_value = cc_html
            rows.append(
                "<tr>"
                '<th style="width:112px;white-space:nowrap;'
                'vertical-align:top;text-align:left;padding:2px 12px 2px 0;">'
                f"{html.escape(label)}</th>"
                '<td style="vertical-align:top;padding:2px 0;">'
                f"{display_value}</td>"
                "</tr>"
            )
        else:
            rows.append(f'<tr><td colspan="2" style="padding:2px 0;">{html.escape(line)}</td></tr>')
    return (
        '<section style="border:1px solid #d0d7de;'
        'padding:12px;margin:0 0 16px 0;'
        'font-family:Meiryo, sans-serif;font-size:14px;">'
        '<table style="border-collapse:collapse;table-layout:auto;">'
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


def compact_date_prefix(value) -> str:
    try:
        if not value:
            return ""
        if hasattr(value, "strftime"):
            date_value = value
        else:
            date_value = datetime.fromisoformat(str(value))
        return date_value.strftime("%y%m%d%H%M%S_")
    except Exception:
        return ""


def make_mail_bookmark_display_name(date_value, sender: str | None, subject: str | None, fallback_subject: str | None) -> str:
    sender_text = str(sender or "").strip() or UNKNOWN_MAIL_SENDER
    subject_text = str(subject or "").strip() or str(fallback_subject or "").strip() or "no_subject"
    return f"{compact_date_prefix(date_value)}{sender_text}_{subject_text}"


def date_prefix(mail_item) -> str:
    return compact_date_prefix(getattr(mail_item, "ReceivedTime", None))


def replace_cid_reference(html_body: str, content_id: str, relative_path: str) -> str:
    cid = re.escape(content_id.strip("<>"))
    return re.sub(f"cid:{cid}", relative_path, html_body, flags=re.IGNORECASE)


def prefer_non_vml_image_fallbacks(html_body: str) -> str:
    pattern = re.compile(
        r"<!--\[if\s+(?:gte\s+)?vml(?:\s+1)?\]>.*?<!\[endif\]-->"
        r"\s*<!\[if\s+!vml\]>(.*?)<!\[endif\]>",
        flags=re.IGNORECASE | re.DOTALL,
    )
    return pattern.sub(lambda match: match.group(1), html_body)


HTML_IMAGE_RE = re.compile(r"<img\b(?P<attrs>[^>]*)>", re.IGNORECASE | re.DOTALL)
HTML_SPAN_RE = re.compile(
    r"<span\b(?P<attrs>[^>]*)>(?P<body>\s*<img\b[^>]*>\s*)</span>",
    re.IGNORECASE | re.DOTALL,
)


def html_attributes(attribute_text: str) -> dict[str, str]:
    pattern = re.compile(r"([:\w-]+)\s*=\s*(['\"])(.*?)\2", re.DOTALL)
    return {match.group(1).lower(): match.group(3) for match in pattern.finditer(attribute_text)}


def css_length_px(style: str, property_name: str) -> float | None:
    match = re.search(rf"(?:^|;)\s*{re.escape(property_name)}\s*:\s*(-?[0-9.]+)(px|pt)?", style, re.I)
    if not match:
        return None
    value = float(match.group(1))
    return value * 96 / 72 if (match.group(2) or "px").lower() == "pt" else value


def local_mail_image_path(mail_dir: Path, source: str | None) -> Path | None:
    source = unquote(str(source or "")).split("?", 1)[0]
    if not source or source.lower().startswith(("cid:", "data:", "http:", "https:")):
        return None
    candidate = (mail_dir / source.replace("/", os.sep)).resolve()
    mail_root = mail_dir.resolve()
    if candidate != mail_root and mail_root not in candidate.parents:
        return None
    return candidate if candidate.is_file() else None


def image_display_size(attributes: dict[str, str]) -> tuple[float, float] | None:
    try:
        width = float(re.sub(r"[^0-9.]", "", attributes.get("width", "")))
        height = float(re.sub(r"[^0-9.]", "", attributes.get("height", "")))
    except ValueError:
        return None
    return (width, height) if width > 0 and height > 0 else None


def make_image_composition_issue(context: str, error: Exception):
    return {
        "category": "Mail image composition error",
        "message": f"Mail overlay image composition failed: {context} -> {error}",
    }


def absolute_image_overlays(html_body: str, mail_dir: Path):
    overlays = []
    for span_match in HTML_SPAN_RE.finditer(html_body):
        span_attributes = html_attributes(span_match.group("attrs"))
        style = span_attributes.get("style", "")
        if "position:absolute" not in style.replace(" ", "").lower():
            continue
        image_match = HTML_IMAGE_RE.search(span_match.group("body"))
        if image_match is None:
            continue
        image_attributes = html_attributes(image_match.group("attrs"))
        values = tuple(css_length_px(style, name) for name in ("margin-left", "margin-top", "width", "height"))
        image_path = local_mail_image_path(mail_dir, image_attributes.get("src"))
        if image_path is None or any(value is None for value in values):
            continue
        overlays.append({
            "match": span_match,
            "path": image_path,
            "left": values[0],
            "top": values[1],
            "width": values[2],
            "height": values[3],
        })
    return overlays


def regular_html_images(html_body: str, mail_dir: Path, overlays):
    overlay_ranges = [(item["match"].start(), item["match"].end()) for item in overlays]
    images = []
    for image_match in HTML_IMAGE_RE.finditer(html_body):
        if any(start <= image_match.start() < end for start, end in overlay_ranges):
            continue
        attributes = html_attributes(image_match.group("attrs"))
        image_path = local_mail_image_path(mail_dir, attributes.get("src"))
        display_size = image_display_size(attributes)
        if image_path is not None and display_size is not None:
            images.append({
                "match": image_match,
                "path": image_path,
                "width": display_size[0],
                "height": display_size[1],
            })
    return images


def overlay_base_image(overlay, images):
    required_width = overlay["left"] + overlay["width"]
    required_height = overlay["top"] + overlay["height"]
    for image in images:
        if image["match"].start() <= overlay["match"].end():
            continue
        if image["width"] >= required_width and image["height"] >= required_height:
            return image
    return None


def compose_overlay_images(base_image, overlays) -> None:
    from PIL import Image

    base_path = base_image["path"]
    temp_path = base_path.with_name(base_path.name + ".composite")
    try:
        with Image.open(base_path) as source:
            image_format = source.format or "PNG"
            canvas = source.convert("RGBA")
        scale_x = canvas.width / base_image["width"]
        scale_y = canvas.height / base_image["height"]
        for overlay in overlays:
            with Image.open(overlay["path"]) as source:
                layer = source.convert("RGBA")
            size = (
                max(1, round(overlay["width"] * scale_x)),
                max(1, round(overlay["height"] * scale_y)),
            )
            layer = layer.resize(size, Image.Resampling.LANCZOS)
            position = (round(overlay["left"] * scale_x), round(overlay["top"] * scale_y))
            canvas.alpha_composite(layer, position)
        output = canvas.convert("RGB") if image_format.upper() in {"JPEG", "JPG"} else canvas
        output.save(temp_path, format=image_format)
        os.replace(temp_path, base_path)
    finally:
        temp_path.unlink(missing_ok=True)


def flatten_absolute_image_overlays(html_body, mail_dir, warnings, context):
    overlays = absolute_image_overlays(html_body, mail_dir)
    if not overlays:
        return html_body
    images = regular_html_images(html_body, mail_dir, overlays)
    groups = {}
    for overlay in overlays:
        base_image = overlay_base_image(overlay, images)
        if base_image is None:
            continue
        key = str(base_image["path"])
        groups.setdefault(key, {"base": base_image, "overlays": []})["overlays"].append(overlay)

    remove_ranges = []
    for group in groups.values():
        try:
            compose_overlay_images(group["base"], group["overlays"])
            remove_ranges.extend(
                (overlay["match"].start(), overlay["match"].end())
                for overlay in group["overlays"]
            )
        except Exception as exc:
            warnings.append(make_image_composition_issue(context, exc))

    for start, end in sorted(remove_ranges, reverse=True):
        html_body = html_body[:start] + html_body[end:]
    return html_body


def eml_date_prefix(message) -> str:
    try:
        return compact_date_prefix(parsedate_to_datetime(message.get("Date")))
    except Exception:
        return ""


def eml_date_value(message):
    try:
        return parsedate_to_datetime(message.get("Date"))
    except Exception:
        return None


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


def msg_direct_parser_available() -> bool:
    try:
        import extract_msg  # noqa: F401
    except ImportError:
        return False
    return True


def import_extract_msg():
    try:
        import extract_msg
    except ImportError:
        return None
    return extract_msg


def decode_bytes_payload(payload: bytes, preferred_encoding: str = "auto") -> str:
    explicit_candidates = unique_texts(
        [
            None if preferred_encoding == "auto" else preferred_encoding,
            *extract_declared_charsets(payload),
        ]
    )
    candidates = unique_texts(
        [
            *explicit_candidates,
            "utf-8-sig",
            "utf-8",
            "cp932",
            "shift_jis",
            "iso-2022-jp",
            "euc-jp",
            *( ["utf-16", "utf-16le", "utf-16be"] if looks_like_utf16(payload) else [] ),
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
    return payload.decode("utf-8", errors="replace")


def msg_value_to_text(value, preferred_encoding: str = "auto") -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return decode_bytes_payload(value, preferred_encoding)
    return str(value)


def extract_msg_body_html(msg, preferred_encoding: str = "auto") -> str:
    html_body = msg_value_to_text(getattr(msg, "htmlBody", None), preferred_encoding)
    if html_body.strip():
        return normalize_html_charset(html_body)
    plain_text = html.escape(msg_value_to_text(getattr(msg, "body", ""), preferred_encoding))
    return f'<html><head><meta charset="utf-8"></head><body><pre>{plain_text}</pre></body></html>'


def attachment_value(attachment, *names):
    for name in names:
        if hasattr(attachment, name):
            value = getattr(attachment, name, None)
            if callable(value):
                try:
                    value = value()
                except TypeError:
                    pass
            if value:
                return value
    return None


def direct_attachment_name(attachment, fallback: str) -> str:
    name = attachment_value(attachment, "longFilename", "shortFilename", "filename", "name")
    return str(name) if name else fallback


def direct_attachment_mime(attachment) -> str:
    value = attachment_value(attachment, "mimetype", "mimeType", "contentType")
    return str(value or "").lower()


def direct_attachment_data(attachment):
    data = attachment_value(attachment, "data")
    return data if isinstance(data, (bytes, bytearray)) else None


def direct_attachment_content_id(attachment) -> str | None:
    value = attachment_value(attachment, "cid", "contentId", "content_id")
    return str(value) if value else None


def is_signature_attachment(file_name: str, mime_type: str) -> bool:
    lower_name = (file_name or "").lower()
    lower_mime = (mime_type or "").lower()
    return (
        lower_name in SIGNATURE_ATTACHMENT_NAMES
        or lower_name.endswith(".p7s")
        or lower_mime in SIGNATURE_MIME_TYPES
    )


def make_signature_ignored_issue(context: str):
    return {
        "category": "Mail signature ignored",
        "message": (
            "Signed/protected mail signature data was ignored while extracting "
            f"normal body and attachments. Context: {safe_text_for_utf8(context)}"
        ),
    }



def msg_has_signature_attachment(msg) -> bool:
    for attachment in list(getattr(msg, "attachments", []) or []):
        file_name = direct_attachment_name(attachment, "")
        mime_type = direct_attachment_mime(attachment)
        if is_signature_attachment(file_name, mime_type):
            return True
    return False


def msg_file_should_use_direct_parser(msg_path: str | Path) -> bool:
    extract_msg = import_extract_msg()
    if extract_msg is None:
        return False
    msg = None
    try:
        msg = extract_msg.Message(str(msg_path))
        return msg_has_signature_attachment(msg)
    except Exception:
        return False
    finally:
        if msg is not None:
            close = getattr(msg, "close", None)
            if callable(close):
                try:
                    close()
                except Exception:
                    pass


def any_msg_file_requires_outlook(paths: Iterable[Path]) -> bool:
    return any(not msg_file_should_use_direct_parser(path) for path in paths)
def export_msg_file_direct(
    msg_path: str | Path,
    work_root: str | Path,
    eml_encoding: str = "auto",
) -> ExportResult | None:
    extract_msg = import_extract_msg()
    if extract_msg is None:
        return None

    msg_path = Path(msg_path)
    work_root = Path(work_root)
    warnings = []
    msg = None
    try:
        msg = extract_msg.Message(str(msg_path))
        attachments = list(getattr(msg, "attachments", []) or [])
        if not msg_has_signature_attachment(msg):
            return None
        raw_subject = getattr(msg, "subject", None) or msg_path.stem
        subject = safe_text_for_utf8(raw_subject, "msg subject")
        append_encoding_issue(warnings, "msg subject", raw_subject, subject)

        raw_date = getattr(msg, "date", "")
        raw_sender = msg_value_to_text(getattr(msg, "sender", ""), eml_encoding)
        sender = safe_text_for_utf8(raw_sender, "msg sender")
        append_encoding_issue(warnings, "msg sender", raw_sender, sender)

        mail_dir = unique_mail_directory(
            work_root,
            make_mail_bookmark_display_name(raw_date, sender, subject, msg_path.stem),
        )
        inline_dir = unique_named_directory(mail_dir, INLINE_IMAGE_DIR_NAME, "i")
        attach_dir = mail_dir / "a00000"

        html_body = extract_msg_body_html(msg, eml_encoding)
        attachment_index = 1
        attachment_names = []
        ignored_signature_count = 0

        for attachment in attachments:
            raw_file_name = direct_attachment_name(attachment, f"attachment_{attachment_index}")
            file_name = safe_text_for_utf8(raw_file_name, "msg attachment name")
            append_encoding_issue(warnings, "msg attachment name", raw_file_name, file_name)
            mime_type = direct_attachment_mime(attachment)
            if is_signature_attachment(file_name, mime_type):
                ignored_signature_count += 1
                continue

            payload = direct_attachment_data(attachment)
            if payload is None:
                continue

            content_id = direct_attachment_content_id(attachment)
            is_inline_image = (
                content_id
                and (mime_type.startswith("image/") or is_emz_file(file_name))
                and f"cid:{content_id.strip('<>')}".lower() in html_body.lower()
            )
            save_path = save_inline_payload(
                payload, inline_dir, file_name, warnings, f"{msg_path}: {file_name}"
            ) if is_inline_image else None
            if save_path is not None:
                relative_path = f"{inline_dir.name}/{save_path.name}"
                html_body = replace_cid_reference(html_body, content_id, relative_path)
            else:
                if not attach_dir.exists():
                    attach_dir = unique_named_directory(mail_dir, ATTACHMENT_DIR_NAME, "a")
                display_name = numbered_attachment_name(attachment_index, file_name)
                save_path = unique_attachment_path(attach_dir, display_name)
                save_path.write_bytes(payload)
                attachment_names.append(display_name)
                attachment_index += 1

        if ignored_signature_count:
            warnings.append(make_signature_ignored_issue(f"{msg_path}; ignored signatures: {ignored_signature_count}"))

        info_item = SimpleNamespace(
            Subject=subject,
            SenderName=msg_value_to_text(getattr(msg, "sender", ""), eml_encoding),
            SenderEmailAddress="",
            To=msg_value_to_text(getattr(msg, "to", ""), eml_encoding),
            CC=msg_value_to_text(getattr(msg, "cc", ""), eml_encoding),
            ReceivedTime=raw_date,
            SentOn=raw_date,
        )
        html_body = prepend_mail_info(
            html_body, mail_info_lines(info_item, attachment_names),
            parsed_to_recipients(info_item.To), parsed_to_recipients(info_item.CC),
        )
        write_body_pdf_and_cleanup(mail_dir, html_body, inline_dir, warnings, "msg body")
        return ExportResult(success=True, source=msg_path, output=mail_dir, warnings=tuple(warnings))
    except Exception as exc:
        return ExportResult(
            success=False,
            source=msg_path,
            error=f"Direct MSG extraction failed: {exc}",
            warnings=tuple(warnings),
        )
    finally:
        if msg is not None:
            close = getattr(msg, "close", None)
            if callable(close):
                try:
                    close()
                except Exception:
                    pass

def export_eml_file(eml_path: str | Path, work_root: str | Path, eml_encoding: str = "auto") -> ExportResult:
    eml_path = Path(eml_path)
    work_root = Path(work_root)
    warnings = []

    try:
        with eml_path.open("rb") as file:
            message = BytesParser(policy=policy.default).parse(file)

        raw_subject = decode_mime_text(message.get("Subject")) or eml_path.stem
        subject = safe_text_for_utf8(raw_subject, "eml subject")
        append_encoding_issue(warnings, "eml subject", raw_subject, subject)
        raw_sender = eml_sender_display(message)
        sender = safe_text_for_utf8(raw_sender, "eml sender")
        append_encoding_issue(warnings, "eml sender", raw_sender, sender)
        mail_dir = unique_mail_directory(
            work_root,
            make_mail_bookmark_display_name(eml_date_value(message), sender, subject, eml_path.stem),
        )
        inline_dir = unique_named_directory(mail_dir, INLINE_IMAGE_DIR_NAME, "i")
        attach_dir = mail_dir / "a00000"

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

            raw_file_name = eml_file_name(part, f"attachment_{attachment_index}")
            file_name = safe_text_for_utf8(raw_file_name, "eml attachment name")
            append_encoding_issue(warnings, "eml attachment name", raw_file_name, file_name)
            content_id = part.get("Content-ID")
            is_inline_image = (
                content_id
                and (content_type.lower().startswith("image/") or is_emz_file(file_name))
                and f"cid:{content_id.strip('<>')}".lower() in html_body.lower()
                and (disposition != "attachment" or is_emz_file(file_name))
            )
            save_path = save_inline_payload(
                payload, inline_dir, file_name, warnings, f"{eml_path}: {file_name}"
            ) if is_inline_image else None
            if save_path is not None:
                relative_path = f"{inline_dir.name}/{save_path.name}"
                html_body = replace_cid_reference(html_body, content_id, relative_path)
            else:
                if not attach_dir.exists():
                    attach_dir = unique_named_directory(mail_dir, ATTACHMENT_DIR_NAME, "a")
                display_name = numbered_attachment_name(attachment_index, file_name)
                save_path = unique_attachment_path(attach_dir, display_name)
                save_path.write_bytes(payload)
                attachment_names.append(display_name)
                attachment_index += 1

        html_body = prepend_mail_info(
            html_body, eml_info_lines(message, attachment_names),
            parsed_to_recipients(message.get("To")), parsed_to_recipients(message.get("Cc")),
        )
        write_body_pdf_and_cleanup(mail_dir, html_body, inline_dir, warnings, "eml body")
        return ExportResult(success=True, source=eml_path, output=mail_dir, warnings=tuple(warnings))
    except Exception as exc:
        return ExportResult(success=False, source=eml_path, error=str(exc), warnings=tuple(warnings))

def export_msg_file(msg_path: str | Path, work_root: str | Path, outlook, eml_encoding: str = "auto") -> ExportResult:
    msg_path = Path(msg_path)
    work_root = Path(work_root)
    item = None
    warnings = []

    try:
        item = run_with_com_retry(lambda: outlook.Session.OpenSharedItem(str(msg_path)), "Microsoft Outlook")
        raw_subject = getattr(item, "Subject", None) or msg_path.stem
        subject = safe_text_for_utf8(raw_subject, "msg subject")
        append_encoding_issue(warnings, "msg subject", raw_subject, subject)

        raw_sender = mail_item_sender_display(item)
        sender = safe_text_for_utf8(raw_sender, "msg sender")
        append_encoding_issue(warnings, "msg sender", raw_sender, sender)

        mail_dir = unique_mail_directory(
            work_root,
            make_mail_bookmark_display_name(getattr(item, "ReceivedTime", None), sender, subject, msg_path.stem),
        )
        inline_dir = unique_named_directory(mail_dir, INLINE_IMAGE_DIR_NAME, "i")
        attach_dir = mail_dir / "a00000"

        html_body = make_html_body(item)
        attachment_count = int(item.Attachments.Count)
        attachment_index = 1
        attachment_names = []

        for index in range(1, attachment_count + 1):
            attachment = None
            try:
                attachment = run_with_com_retry(lambda: item.Attachments.Item(index), "Microsoft Outlook")
                raw_file_name = getattr(attachment, "FileName", None) or f"attachment_{index}"
                file_name = safe_text_for_utf8(raw_file_name, "msg attachment name")
                append_encoding_issue(warnings, "msg attachment name", raw_file_name, file_name)

                content_id = get_content_id(attachment)
                save_path = save_outlook_inline_attachment(
                    attachment, inline_dir, file_name, warnings, f"{msg_path}: {file_name}"
                ) if is_inline_attachment(attachment, html_body) else None
                if save_path is not None:
                    relative_path = f"{inline_dir.name}/{save_path.name}"
                    html_body = replace_cid_reference(html_body, content_id, relative_path)
                else:
                    if not attach_dir.exists():
                        attach_dir = unique_named_directory(mail_dir, ATTACHMENT_DIR_NAME, "a")
                    display_name = numbered_attachment_name(attachment_index, file_name)
                    save_path = unique_attachment_path(attach_dir, display_name)
                    run_with_com_retry(lambda: attachment.SaveAsFile(str(save_path)), "Microsoft Outlook")
                    attachment_names.append(display_name)
                    attachment_index += 1
            finally:
                if attachment is not None:
                    release_com_object(attachment)

        html_body = prepend_mail_info(
            html_body, mail_info_lines(item, attachment_names),
            outlook_to_recipients(item), outlook_cc_recipients(item),
        )
        write_body_pdf_and_cleanup(mail_dir, html_body, inline_dir, warnings, "msg body")

        close_mail_item(item)
        item = None
        return ExportResult(success=True, source=msg_path, output=mail_dir, warnings=tuple(warnings))
    except Exception as exc:
        return ExportResult(success=False, source=msg_path, error=str(exc), warnings=tuple(warnings))
    finally:
        if item is not None:
            release_com_object(item)

def export_mail_file(
    mail_path: str | Path,
    work_root: str | Path,
    outlook=None,
    eml_encoding: str = "auto",
) -> ExportResult:
    mail_path = Path(mail_path)
    work_root = Path(work_root)
    mailbox_extension = mail_path.suffix.lower()

    if mailbox_extension == ".msg":
        direct_result = export_msg_file_direct(mail_path, work_root, eml_encoding)
        if direct_result is not None and direct_result.success:
            return direct_result
        created_outlook = False
        if outlook is None:
            outlook = create_outlook_application()
            created_outlook = True
        try:
            fallback_result = export_msg_file(mail_path, work_root, outlook, eml_encoding)
        finally:
            if created_outlook:
                release_com_object(outlook)
                uninitialize_com()
        if direct_result is not None and direct_result.error:
            fallback_warnings = list(getattr(fallback_result, "warnings", ()))
            fallback_warnings.extend(getattr(direct_result, "warnings", ()))
            fallback_warnings.append(
                {
                    "category": "Direct MSG extraction fallback",
                    "message": (
                        "Direct MSG extraction failed, so Outlook conversion was used. "
                        f"{direct_result.error}"
                    ),
                }
            )
            return ExportResult(
                success=fallback_result.success,
                source=fallback_result.source,
                output=fallback_result.output,
                error=fallback_result.error,
                warnings=tuple(fallback_warnings),
            )
        return fallback_result
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
        outlook = win32com.client.Dispatch("Outlook.Application")
        time.sleep(OFFICE_COM_STARTUP_WAIT_SECONDS)
        return outlook
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

    msg_files = [path for path in files if path.suffix.lower() == ".msg"]
    outreach = create_outlook_application() if msg_files and any_msg_file_requires_outlook(msg_files) else None
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
            time.sleep(MAIL_EXPORT_COOLDOWN_SECONDS)
            results.append(result)
    finally:
        if outreach is not None:
            release_com_object(outreach)
            uninitialize_com()
    return results


def expand_mail_file(mail_path: str | Path, destination_folder: str | Path, outlook=None, eml_encoding: str = "auto") -> ExportResult:
    return export_mail_file(mail_path, destination_folder, outlook=outlook, eml_encoding=eml_encoding)
