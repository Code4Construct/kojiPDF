import os

from fitz import Document


def get_each_pdf_toc(df):
    """
    Return each source PDF's TOC keyed by merged-page start and PDF title.
    """
    results = {}

    if not df:
        return results
    if "Full Path" not in df[0]:
        raise ValueError("tree rowsに 'Full Path' が見つかりません。")

    level_cols = [
        column
        for row in df
        for column in row.keys()
        if column.strip().startswith("Level ")
    ]
    level_cols = sorted(set(level_cols), key=lambda x: int(x.split()[-1]))
    level_count = len(level_cols)

    for row in df:
        page = row.get("Page All", None)
        if page is None:
            continue
        page += 1

        path = row.get("Full Path", None)
        levels = [row.get(f"Level {i + 1}", "") for i in range(level_count)]
        pdf_title = next(
            (level for level in reversed(levels) if isinstance(level, str) and level.lower().endswith(".pdf")),
            None,
        )

        if not path or not os.path.exists(path) or not pdf_title:
            continue

        try:
            with Document(path) as pdf_document:
                toc = pdf_document.get_toc()
                if toc:
                    results[(page, pdf_title)] = toc

        except Exception as e:
            print(f"[エラー] PDFを処理中に問題が発生しました: {path} - {e}")

    return results


if __name__ == "__main__":
    import m01make_treedata as tree_data
    import m04file_name_replace as tree_data_cleanup

    df, _ = tree_data.build_tree_data(".")
    df = tree_data_cleanup.prepare_treedata_for_merge(df)
    toc_dict = get_each_pdf_toc(df)

    for (page, title), toc in toc_dict.items():
        print(f"{page} - {title}")
        for item in toc:
            print("  ", item)
