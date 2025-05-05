import fitz  # PyMuPDF

def get_pdf_page_xyr(pdf_document):
    """
    PDFの各ページの幅、高さ、回転角度を取得し、辞書として返す。

    Args:
        pdf_path (str): 対象のPDFファイルのパス。

    Returns:
        dict: ページ番号をキー、(幅, 高さ, 回転角度) のタプルを値とする辞書。
    """
    print("　ページ番号をキーとして(幅, 高さ, 回転角度) のタプルを値とする辞書として取得しています。")
    page_info = {}

    # PDFの各ページを取得
    for page_num in range(len(pdf_document)):
        page = pdf_document[page_num]
        rect = page.rect  # ページのサイズ情報
        rotation = page.rotation  # ページの回転角度

        # 幅・高さを mm 単位に変換 (72dpi基準 → mm に換算)
        width_mm = rect.width / 72 * 25.4
        height_mm = rect.height / 72 * 25.4
        # 辞書にページ情報を追加
        page_info[page_num + 1] = (width_mm, height_mm, rotation)
    return page_info


if __name__ == "__main__":
    # 使用例
    pdf_path = r"c:\Users\uboni\Desktop\検査用栞付結合データ.pdf"  # PDFのパスを指定
    pdf_document = fitz.open(pdf_path)
    info = get_pdf_page_xyr(pdf_document)

    # 結果を表示
    for page, (width, height, rotation) in info.items():
        if 1 <= page<=600 or 15500 <= page<=15600:
            print(f"Page {page}: Width = {width:.2f} mm, Height = {height:.2f} mm, Rotation = {rotation} degrees")
