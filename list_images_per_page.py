import os
import fitz  # PyMuPDF

def list_images_per_page(pdf_path):
    """
    指定されたPDFファイル内の各ページに含まれる画像情報をリストで返す。

    Args:
        pdf_path (str): PDFファイルのパス

    Returns:
        list: 各ページごとの画像情報のリスト
    """
    doc = fitz.open(pdf_path)
    result = []

    for page_number in range(len(doc)):
        page = doc.load_page(page_number)
        images = page.get_images(full=True)
        page_info = {"page": page_number + 1, "images": [], "text_size": 0, "font_size": 0}

        # 画像情報を収集
        for img_index, img in enumerate(images):
            xref = img[0]
            width = img[2]
            height = img[3]
            img_info = doc.extract_image(xref)
            img_bytes = img_info["image"]
            img_size = len(img_bytes)

            page_info["images"].append({
                "index": img_index,
                "width": width,
                "height": height,
                "size_bytes": img_size
            })

        # テキスト情報のサイズを収集
        text = page.get_text("text")
        page_info["text_size"] = len(text.encode("utf-8"))  # テキストのバイトサイズ

        # フォントデータサイズを収集
        fonts = page.get_fonts(full=True)
        for font in fonts:
            page_info["font_size"] += len(font[3].encode("utf-8"))  # フォントの名前のサイズを計算

        result.append(page_info)

    doc.close()
    return result

def analyze_pdf_capacity(pdf_path):
    """
    PDFファイルの全体容量、メタデータ、フォント情報を分析する。

    Args:
        pdf_path (str): PDFファイルのパス

    Returns:
        dict: PDFの容量に関する情報
    """
    doc = fitz.open(pdf_path)

    # PDFのメタデータを取得
    metadata = doc.metadata
    metadata_size = 0
    if metadata:
        metadata_size = sum(len(value.encode('utf-8')) for value in metadata.values() if value)  # メタデータのサイズをバイト単位で計算

    # PDF全体サイズを取得
    pdf_total_size = os.path.getsize(pdf_path)

    total_image_size = 0  # 画像データ合計
    total_text_size = 0   # テキストデータ合計
    total_font_size = 0   # フォントデータ合計

    pages_info = list_images_per_page(pdf_path)

    # 結果を集計
    for page in pages_info:
        total_image_size += sum(img['size_bytes'] for img in page['images'])
        total_text_size += page['text_size']
        total_font_size += page['font_size']

    # フォント情報
    font_data_size = total_font_size  # フォントデータのサイズ

    doc.close()

    return {
        "pdf_total_size": pdf_total_size,
        "total_image_size": total_image_size,
        "total_text_size": total_text_size,
        "metadata_size": metadata_size,
        "font_data_size": font_data_size,
        "image_and_text_other_data_size": pdf_total_size - total_image_size - total_text_size,
        "image_and_text_and_metadata_other_data_size": pdf_total_size - total_image_size - total_text_size - metadata_size
    }

if __name__ == "__main__":
    # PDFファイルのパスを指定
    pdf_path = r"C:\Users\uboni\Downloads\目標管理.pdf"

    # PDFの容量分析
    pdf_capacity = analyze_pdf_capacity(pdf_path)

    # 結果の表示
    print(f"\n--- 集計 ---")
    print(f"PDF全体サイズ       : {pdf_capacity['pdf_total_size'] / 1024:.1f} KB")
    print(f"画像データ合計サイズ : {pdf_capacity['total_image_size'] / 1024:.1f} KB")
    print(f"テキストデータ合計サイズ: {pdf_capacity['total_text_size'] / 1024:.1f} KB")
    print(f"メタデータサイズ      : {pdf_capacity['metadata_size'] / 1024:.1f} KB")
    print(f"フォントデータサイズ  : {pdf_capacity['font_data_size'] / 1024:.1f} KB")
    print(f"画像以外のデータ量   : {(pdf_capacity['pdf_total_size'] - pdf_capacity['total_image_size']) / 1024:.1f} KB")
    print(f"画像とテキスト以外のデータ量   : {pdf_capacity['image_and_text_other_data_size'] / 1024:.1f} KB")
    print(f"画像とテキストとメタデータ以外のデータ量   : {pdf_capacity['image_and_text_and_metadata_other_data_size'] / 1024:.1f} KB")
