from fitz import open as fitz_open


def add_bookmarks_to_pdf(df, N, pdf_document):
    last_bookmarks = [None] * N
    for row in df:
        page_count = row.get("Page Count", 0)
        page_all = row.get("Page All", None)
        levels = [row.get(f"Level {i + 1}", "") for i in range(N)]

        if page_count != 0 and page_all is not None:
            page_index = int(page_all)
            preleveladd = False
            if 0 <= page_index < len(pdf_document):
                for level, text in enumerate(levels, start=1):
                    if (preleveladd or text != last_bookmarks[level - 1]) and str(text) not in ("None", ""):
                        pdf_document.set_toc(pdf_document.get_toc() + [(level, str(text), page_index + 1, 0)])
                        last_bookmarks[level - 1] = text
                        preleveladd = True
                    else:
                        preleveladd = False
            else:
                continue

    return pdf_document


if __name__ == "__main__":
    import m01make_treedata as tree_data
    import m04file_name_replace as tree_data_cleanup

    df, N = tree_data.build_tree_data(".")
    df = tree_data_cleanup.prepare_treedata_for_merge(df)
    pdf_document = fitz_open("merged_output.pdf")
    add_bookmarks_to_pdf(df, N, pdf_document)
