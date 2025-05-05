import fitz

def add_page_number_to_bookmarks(output_pdf):
    """
    PDF のしおり（ブックマーク）にページ番号の差分を追加します。

    各しおりのタイトルの末尾に、次の同レベル以下のしおりまでのページ差分を付加します。
    
    Args:
        output_pdf (fitz.Document): 処理対象の PDF ドキュメント。

    Returns:
        fitz.Document: ページ番号付きのしおりを追加した PDF ドキュメント。
    """
    toc = output_pdf.get_toc()
    new_toc = []
    
    for i, entry in enumerate(toc):
        level, title, page = entry[:3]  # しおりの基本情報を取得
        
        # 次の自身のlevel以下のしおりを探す
        next_page = output_pdf.page_count + 1
        for j in range(i + 1, len(toc)):
            if toc[j][0] <= level:  # 自分のlevel以下の最初のしおり
                next_page = toc[j][2]
                break
        
        page_diff = next_page - page  # 次の適切なしおりまでのページ差分
        new_title = f"{title}_{page_diff}"  # タイトルの後ろに差分を追加
        new_entry = [level, new_title, page] + entry[3:]  # 追加情報があれば保持
        new_toc.append(new_entry)
    
    output_pdf.set_toc(new_toc)
    return output_pdf

if __name__ == "__main__":
    input_path = r"C:\Users\uboni\Desktop\検査用栞付結合データtemp.PDF"
    output_path = r"C:\Users\uboni\Desktop\検査用栞付結合データnum.PDF"
    
    output_pdf = fitz.open(input_path)
    output_pdf = add_page_number_to_bookmarks(output_pdf)
    output_pdf.save(output_path)
    output_pdf.close()


