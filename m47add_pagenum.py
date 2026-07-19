from pathlib import Path
import fitz  # PyMuPDF


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


def add_page_numbers_to_doc(
    doc,
    start_number=1,
    font_size=30,
    margin_right=10,
    margin_bottom=10,
    fontname="helv",
    fill=(0, 0, 0),
    fill_opacity=1.0,
):
    for page_index, page in enumerate(doc, start=start_number):
        page.wrap_contents()
        pad_content_stream_boundaries(page)
        rect = page.rect
        rotation = page.rotation % 360
        if rotation not in (0, 90, 180, 270):
            rotation = 0
        text = str(page_index)

        # 文字幅を計算
        text_width = fitz.get_text_length(
            text,
            fontname=fontname,
            fontsize=font_size,
        )

        x = rect.width - margin_right - text_width
        y = rect.height - margin_bottom
        point = fitz.Point(x, y) * page.derotation_matrix

        shape = page.new_shape()
        shape.insert_text(
            point,
            text,
            fontsize=font_size,
            fontname=fontname,
            fill=fill,
            fill_opacity=fill_opacity,
            rotate=rotation,
        )
        shape.commit(overlay=True)

        print(f"page {page_index} added")

    return doc


# --------------------------------------------------
# メイン実行（コピペで使える）
# --------------------------------------------------
if __name__ == "__main__":
    TARGET_PDF = Path(r"C:\Users\uboni\Downloads\検査用栞付結合データtemp.PDF")

    # ① 開く
    doc = fitz.open(TARGET_PDF)

    # ② 加工
    doc = add_page_numbers_to_doc(
        doc,
        start_number=1,
        font_size=30,
        margin_right=10,
        margin_bottom=10,
        fontname="helv",
        fill=(1, 0, 0),       # 赤
        fill_opacity=0.2,     # 半透明
    )

    # ③ 安全に保存（上書き）
    tmp_path = TARGET_PDF.with_suffix(".tmp.pdf")

    doc.save(
        tmp_path,
        garbage=1,
        deflate=True,
        # pdf_version="1.4",  # 必要なら透明度安定用
    )
    doc.close()

    tmp_path.replace(TARGET_PDF)

    print(f"✅ 完了: {TARGET_PDF}")
