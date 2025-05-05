# pdfdocument.py
import fitz  # PyMuPDF

def get_fonts(pdf_document):
    """
    PDFドキュメントからしおり情報を取得し、しおりタイトルとページ番号に対応する
    スタイル（色、太字、斜体）を辞書形式で返す関数。

    スタイルの決定ルールは以下の通り：
    - タイトルが "打_" で始まり、かつ ".pdf" を含む場合：赤色（(0.7, 0, 0)）、標準（太字・斜体なし）
    - タイトルが "打_" で始まらず、かつ ".pdf" を含む場合：青色（(0, 0, 0.7)）、標準（太字・斜体なし）
    - その他：黒色（(0, 0, 0)）、標準（太字・斜体なし）

    Parameters:
        pdf_document: PyMuPDF（fitz）などのPDFオブジェクト。get_toc() メソッドを持っている必要がある。

    Returns:
        dict: {(タイトル, ページ番号): (色タプル, 太字, 斜体)} の形式の辞書
    """
    print("　しおり名とページ番号をキーとしたスタイル情報を辞書形式で作成しています。")
    style_dict = {}
    for bookmark in pdf_document.get_toc():
        level, title, page = bookmark  # しおりのレベル、タイトル、ページ番号
        
        if title.startswith("打_") and ".pdf" in title:
            color = (0.7, 0, 0)  # 赤
            bold = False
            italic = False
        elif not title.startswith("打_") and ".pdf" in title:
            color = (0,0,0.7)  # 青
            bold = False
            italic = False
        else:
            color = (0, 0, 0)  # 黒
            bold = False
            italic = False
        
        style_dict[title,page] = (color, bold, italic)
    
    return style_dict

if __name__ == "__main__":
    pdf_path = r"C:\Users\uboni\Desktop\検査用栞付結合データ.pdf"
    pdf_document = fitz.open(pdf_path)
    
    # しおり情報取得
    bookmark_styles = get_fonts(pdf_document)
    
    # しおりのスタイル情報を表示
    for title, page in bookmark_styles.items():
        print(bookmark_styles.get(title,page))


    
