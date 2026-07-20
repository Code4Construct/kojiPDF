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
    position="bottom_right",
    number_format="number",
    start_page=1,
    start_number=1,
    font_size=30,
    margin_x=None,
    margin_y=None,
    margin_right=10,
    margin_bottom=10,
    fontname="helv",
    fill=(0, 0, 0),
    fill_opacity=1.0,
):
    margin_x = margin_right if margin_x is None else margin_x
    margin_y = margin_bottom if margin_y is None else margin_y
    start_page = max(1, int(start_page))
    total_pages = len(doc)

    def page_number_text(number):
        if number_format == "page_number":
            return f"Page {number}"
        if number_format == "number_total":
            return f"{number} / {total_pages}"
        if number_format == "page_of_total":
            return f"Page {number} of {total_pages}"
        if number_format == "p_number":
            return f"p.{number}"
        if number_format == "no_number":
            return f"No.{number}"
        if number_format == "dash_number":
            return f"- {number} -"
        if number_format == "bracket_number":
            return f"【{number}】"
        return str(number)

    def text_point(rect, text_width):
        if position.endswith("_left"):
            x = margin_x
        elif position.endswith("_center"):
            x = (rect.width - text_width) / 2
        else:
            x = rect.width - margin_x - text_width

        if position.startswith("top_"):
            y = margin_y + font_size
        else:
            y = rect.height - margin_y

        return fitz.Point(x, y)

    for page_index, page in enumerate(doc, start=1):
        if page_index < start_page:
            continue

        printed_number = start_number + page_index - start_page
        page.wrap_contents()
        pad_content_stream_boundaries(page)
        rect = page.rect
        rotation = page.rotation % 360
        if rotation not in (0, 90, 180, 270):
            rotation = 0
        text = page_number_text(printed_number)

        # 文字幅を計算
        text_width = fitz.get_text_length(
            text,
            fontname=fontname,
            fontsize=font_size,
        )

        point = text_point(rect, text_width) * page.derotation_matrix

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
