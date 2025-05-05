def add_children_to_existing_toc(doc, toc_dict):
    """
    すでに親しおりが設定された `doc` に、`toc_dict` の情報を元に子しおりを追加します。
    
    Parameters:
        doc (fitz.Document): すでに読み込まれた PDF ドキュメント
        toc_dict (dict): {(page, pdf_title): [[level, title, page], ...]} の形式のしおり辞書
    
    Returns:
        fitz.Document: 子しおりが追加された PDF ドキュメント
    """
    original_toc = doc.get_toc()
    updated_toc = []

    for parent in original_toc:
        level, title, page = parent
        updated_toc.append(parent)

        # 親の (page, title) に一致する子しおりを追加
        children = toc_dict.get((page, title), [])
        for entry in children:
            child_level, child_title, child_page = entry
            if isinstance(child_page, int):
                actual_page = page + child_page - 1  # 結合PDF上での実ページ番号に補正
                updated_toc.append([level + child_level, child_title, actual_page])

    doc.set_toc(updated_toc)
    return doc
