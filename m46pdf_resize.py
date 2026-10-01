from pathlib import Path
import re
from urllib.parse import quote, unquote

import fitz  # PyMuPDF


PAGE_SIZES = {
    "A3": (842, 1191),
    "A4": (595, 842),
    "A5": (420, 595),
    "B4": (729, 1032),
    "B5": (516, 729),
}


def get_size(size):
    if isinstance(size, str):
        return PAGE_SIZES[size.upper()]
    return size


def pad_content_stream_boundaries(page):
    doc = page.parent
    for xref in page.get_contents():
        stream = doc.xref_stream(xref)
        if not stream:
            continue

        padded = stream
        if padded[:1] not in b"\x00\t\n\f\r ":
            padded = b"\n" + padded
        if padded[-1:] not in b"\x00\t\n\f\r ":
            padded = padded + b"\n"

        if padded != stream:
            doc.update_stream(xref, padded)


def get_content_rect(page, padding=4):
    rects = []
    page_rect = page.cropbox

    for _, bbox in page.get_bboxlog():
        rect = fitz.Rect(bbox)
        if rect.is_empty or rect.is_infinite:
            continue
        rect = rect & page_rect
        if not rect.is_empty:
            rects.append(rect)

    if not rects:
        return page_rect

    content_rect = rects[0]
    for rect in rects[1:]:
        content_rect |= rect

    content_rect.x0 = max(page_rect.x0, content_rect.x0 - padding)
    content_rect.y0 = max(page_rect.y0, content_rect.y0 - padding)
    content_rect.x1 = min(page_rect.x1, content_rect.x1 + padding)
    content_rect.y1 = min(page_rect.y1, content_rect.y1 + padding)
    return content_rect


def has_annotations(doc):
    return any(page.first_annot is not None for page in doc)


def bake_annotations_into_content(doc):
    if not has_annotations(doc):
        return doc

    if not hasattr(doc, "bake"):
        raise RuntimeError(
            "PDF注釈を本文へ焼き込むには PyMuPDF 1.24.2 以上が必要です。"
            "requirements.txt に従って PyMuPDF を更新してください。"
        )

    doc.bake(annots=True, widgets=True)
    return doc


def copy_link(link, page=None):
    copied = dict(link)
    copied.pop("xref", None)
    copied.pop("id", None)
    if page is None:
        copied["from"] = fitz.Rect(copied["from"])
    else:
        copied["from"] = normalize_link_rect(page, copied["from"])
    return copied


def file_path_to_uri(file_path):
    if not file_path:
        return None

    path = str(file_path).strip().replace("\\", "/")
    if not path:
        return None

    if path.lower().startswith("file:"):
        path = path[5:]
        if re.match(r"^//+[A-Za-z]:/", path):
            path = "/" + path.lstrip("/")
            return "file://" + quote(unquote(path), safe="/:~!$&'()*+,;=@")
        if path.startswith("//"):
            path = "//" + path.lstrip("/")
            return "file:" + quote(unquote(path), safe="/:~!$&'()*+,;=@")
        return "file:" + quote(unquote(path), safe="/:~!$&'()*+,;=@")

    if re.match(r"^[A-Za-z]:/", path):
        path = "/" + path

    if re.match(r"^//+[A-Za-z]:/", path):
        path = "/" + path.lstrip("/")
        return "file://" + quote(unquote(path), safe="/:~!$&'()*+,;=@")

    if re.match(r"^/[A-Za-z]:/", path):
        return "file://" + quote(unquote(path), safe="/:~!$&'()*+,;=@")

    if path.startswith("//"):
        path = "//" + path.lstrip("/")
        return "file:" + quote(unquote(path), safe="/:~!$&'()*+,;=@")

    if path.startswith("/"):
        return "file://" + quote(unquote(path), safe="/:~!$&'()*+,;=@")

    return None


def original_launch_target(doc, link):
    xref = link.get("xref")
    if doc is None or not xref or link.get("kind") not in (fitz.LINK_LAUNCH, fitz.LINK_GOTOR):
        return None

    # Word writes UTF-8 file paths as hex strings. Read them before get_links()
    # drops a slash or percent-encodes the filename.
    action = doc.xref_object(xref)
    for key in ("UF", "F"):
        match = re.search(r"/" + key + r"\s*<([0-9A-Fa-f]+)>", action)
        if match:
            try:
                return bytes.fromhex(match.group(1)).decode("utf-8").replace("\\", "/")
            except (ValueError, UnicodeDecodeError):
                pass

    for key in ("A/F/UF", "A/F/F"):
        kind, value = doc.xref_get_key(xref, key)
        if kind == "string":
            return value.replace("\\", "/")
    return None


def original_file_uri(doc, link):
    xref = link.get("xref")
    if doc is None or not xref:
        return None
    kind, value = doc.xref_get_key(xref, "A/URI")
    return value if kind == "string" and value.lower().startswith("file:") else None


def normalize_file_link(link, doc=None):
    uri = original_file_uri(doc, link)
    if uri is None:
        file_path = original_launch_target(doc, link) or link.get("file")
        uri = file_path_to_uri(file_path)
    if uri is None:
        return link

    return {
        "kind": fitz.LINK_URI,
        "from": fitz.Rect(link["from"]),
        "uri": uri,
    }


def normalize_file_links_as_uri_doc(doc):
    for page in doc:
        links = list(page.get_links())
        for link in links:
            normalized_link = normalize_file_link(link, doc)
            if normalized_link is link:
                continue
            try:
                page.delete_link(link)
                page.insert_link(normalized_link)
            except Exception as exc:
                print(f"file link normalize skipped: {exc}")
    return doc


def collect_page_links(doc):
    return [[copy_link(normalize_file_link(link, doc), page) for link in page.get_links()] for page in doc]



def transformed_rect(rect, matrix):
    source = fitz.Rect(rect)
    points = [
        source.tl * matrix,
        source.tr * matrix,
        source.bl * matrix,
        source.br * matrix,
    ]
    result = fitz.Rect(points[0], points[0])
    for point in points[1:]:
        result |= fitz.Rect(point, point)
    return result


def normalize_link_rect(page, rect):
    rotation = page.rotation % 360
    if rotation not in (90, 180, 270):
        return fitz.Rect(rect)
    return transformed_rect(rect, page.rotation_matrix)


def scale_link_rect(rect, target_rect, scale):
    source = fitz.Rect(rect)
    return fitz.Rect(
        target_rect.x0 + source.x0 * scale,
        target_rect.y0 + source.y0 * scale,
        target_rect.x0 + source.x1 * scale,
        target_rect.y0 + source.y1 * scale,
    )


def insert_page_links(page, links):
    for link in links:
        try:
            page.insert_link(link)
        except Exception as exc:
            print(f"link restore skipped: {exc}")


def normalize_rotation_doc(src_doc):
    normalized_doc = fitz.open()

    for page in src_doc:
        rotation = page.rotation % 360
        if rotation not in (0, 90, 180, 270):
            rotation = 0

        one_page_doc = fitz.open()
        one_page_doc.insert_pdf(src_doc, from_page=page.number, to_page=page.number)
        pad_content_stream_boundaries(one_page_doc[0])
        one_page_doc[0].set_rotation(0)

        target_page = normalized_doc.new_page(width=page.rect.width, height=page.rect.height)
        target_page.show_pdf_page(
            target_page.rect,
            one_page_doc,
            0,
            rotate=(-rotation) % 360,
        )
        one_page_doc.close()

        print(f"page {page.number + 1} rotation normalized ({rotation}->0)")

    return normalized_doc


def resize_doc_auto_orientation(src_doc, size="A4"):
    base_w, base_h = get_size(size)
    source_links = collect_page_links(src_doc)
    bake_annotations_into_content(src_doc)
    normalized_doc = normalize_rotation_doc(src_doc)
    dst_doc = fitz.open()

    for page in normalized_doc:
        page_rect = page.rect
        visual_width, visual_height = page_rect.width, page_rect.height

        if visual_width > visual_height:
            target_w, target_h = max(base_w, base_h), min(base_w, base_h)
        else:
            target_w, target_h = min(base_w, base_h), max(base_w, base_h)

        scale = min(target_w / visual_width, target_h / visual_height)

        new_w = visual_width * scale
        new_h = visual_height * scale

        x = (target_w - new_w) / 2
        y = (target_h - new_h) / 2

        target_rect = fitz.Rect(x, y, x + new_w, y + new_h)

        new_page = dst_doc.new_page(width=target_w, height=target_h)
        new_page.show_pdf_page(target_rect, normalized_doc, page.number)
        links = []
        for link in source_links[page.number]:
            restored_link = dict(link)
            restored_link["from"] = scale_link_rect(restored_link["from"], target_rect, scale)
            links.append(restored_link)
        insert_page_links(new_page, links)

        print(f"page {page.number + 1} resized")

    normalized_doc.close()

    return dst_doc


if __name__ == "__main__":
    TARGET_PDF = Path(r"C:\Users\SampleUser\Downloads\検査用栞付結合データtemp.PDF")
    TARGET_SIZE = "A4"

    src_doc = fitz.open(TARGET_PDF)

    resized_doc = resize_doc_auto_orientation(
        src_doc,
        size=TARGET_SIZE,
    )

    src_doc.close()

    tmp_path = TARGET_PDF.with_name(TARGET_PDF.stem + "_resized_tmp.pdf")

    resized_doc.save(
        tmp_path,
        garbage=1,
        deflate=True,
    )
    resized_doc.close()

    tmp_path.replace(TARGET_PDF)

    print(f"✅ 完了: {TARGET_PDF}")
