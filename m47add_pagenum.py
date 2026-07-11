from pathlib import Path
import fitz  # PyMuPDF


def add_page_numbers_to_doc(
    doc,
    start_number=1,
    font_size=20,
    margin_right=30,
    margin_bottom=25,
    fontname="helv",
    fill=(0, 0, 0),
    fill_opacity=1.0,
):
    for page_index, page in enumerate(doc, start=start_number):
        rect = page.rect
        text = str(page_index)

        # 文字幅を計算
        text_width = fitz.get_text_length(
            text,
            fontname=fontname,
            fontsize=font_size,
        )

        x = rect.width - margin_right - text_width
        y = rect.height - margin_bottom

        page.insert_text(
            fitz.Point(x, y),
            text,
            fontsize=font_size,
            fontname=fontname,
            fill=fill,
            fill_opacity=fill_opacity,
        )

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
        font_size=100,
        margin_right=30,
        margin_bottom=25,
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