from pathlib import Path
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

        print(f"page {page.number + 1} resized")

    normalized_doc.close()

    return dst_doc


if __name__ == "__main__":
    TARGET_PDF = Path(r"C:\Users\uboni\Downloads\検査用栞付結合データtemp.PDF")
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
