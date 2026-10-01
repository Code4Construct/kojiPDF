import re


PDF_EXTENSION_SUFFIX_RE = re.compile(r"\.pdf(?=(?:_\d+)*$)", re.IGNORECASE)


def prepare_treedata_for_merge(df):
    """
    Sort tree rows and add the cumulative starting page as ``Page All``.
    """
    sorted_rows = sorted((row.copy() for row in df), key=lambda row: row.get("sortpath", ""))
    page_all = 0
    for row in sorted_rows:
        row["Page All"] = page_all
        page_all += int(row.get("Page Count") or 0)
    return sorted_rows


def remove_pdf_extension_suffix(value):
    if not isinstance(value, str):
        return value
    return PDF_EXTENSION_SUFFIX_RE.sub("", value)


def remove_pdf_extensions_from_level_titles(df):
    cleaned_rows = []
    for row in df:
        cleaned = row.copy()
        for key, value in row.items():
            if isinstance(key, str) and key.strip().startswith("Level "):
                cleaned[key] = remove_pdf_extension_suffix(value)
        cleaned_rows.append(cleaned)
    return cleaned_rows


def remove_pdf_extensions_from_toc_keys(toc_dict):
    cleaned = {}
    for key, toc in toc_dict.items():
        if (
            isinstance(key, tuple)
            and len(key) == 2
        ):
            page, title = key
            cleaned[(page, remove_pdf_extension_suffix(title))] = toc
        else:
            cleaned[key] = toc
    return cleaned


def modify_pdf_names_in_all_columns(df):
    """
    Compatibility wrapper: apply ASPer name cleanup, then prepare merge data.
    """
    import m14asper_format as asper_format

    return prepare_treedata_for_merge(asper_format.modify_pdf_names_in_all_columns(df))


if __name__ == "__main__":
    data = [
        {
            "column1": "縲先悽譁・粗xample1.pdf",
            "Full Path": "C:/path/to/12-file1.pdf",
            "column3": "34-textfile.doc",
            "Page Count": 1,
            "sortpath": "C:/path/to/12-file1.pdf",
        },
        {
            "column1": "example2.txt",
            "Full Path": "C:/path/to/file2.pdf",
            "column3": "78-example7.pdf",
            "Page Count": 1,
            "sortpath": "C:/path/to/file2.pdf",
        },
    ]
    print(modify_pdf_names_in_all_columns(data))
