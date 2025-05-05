import fitz

def last_bookmarks_rename(output_pdf):
    """
    PDF のしおり（ブックマーク）を修正します。

    修正内容:
    - しおりの語尾にナンバーをつける処理を削除
    - しおりの文頭が "ｶ鑑_" の場合、 "打_" に変更
    - しおりの文頭が "ﾃXX_"（XX は半角数字 2 文字）の場合、その部分を削除
    
    Args:
        output_pdf (fitz.Document): 処理対象の PDF ドキュメント。

    Returns:
        fitz.Document: 修正後のしおりを持つ PDF ドキュメント。
    """
    toc = output_pdf.get_toc()
    new_toc = []
    
    for entry in toc:
        level, title, page = entry[:3]  # しおりの基本情報を取得
        
        # 文頭が "ｶ鑑_" の場合、 "打_" に変更
        if title.startswith("ｶ鑑_"):
            title = "打_" + title[3:]
        
        # 文頭が "ﾃXX_"（XX は半角数字 2 文字）の場合、その部分を削除
        elif len(title) > 4 and title[0] == "ﾃ" and title[1:3].isdigit() and title[3] == "_":
            title = title[4:]
        
        new_entry = [level, title, page] + entry[3:]  # 追加情報があれば保持
        new_toc.append(new_entry)
    
    output_pdf.set_toc(new_toc)
    return output_pdf

if __name__ == "__main__":
    input_path = r"C:\Users\uboni\Desktop\検査用栞付結合データtemp.PDF"
    output_path = r"C:\Users\uboni\Desktop\検査用栞付結合データrename.PDF"
    
    output_pdf = fitz.open(input_path)
    output_pdf = last_bookmarks_rename(output_pdf)
    output_pdf.save(output_path)
    output_pdf.close()
