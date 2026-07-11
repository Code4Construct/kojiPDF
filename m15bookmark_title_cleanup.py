import re


def _copy_bookmark_destination(destination):
    if not isinstance(destination, dict):
        return destination

    copied = dict(destination)
    copied.pop("xref", None)
    return copied


def remove_pdf_extension_from_bookmarks(pdf_document, collapse=1):
    """
    しおり名の末尾にある .pdf を削除します。

    TOC のリンク情報や色などの追加情報は保持します。
    """
    new_toc = []
    for entry in pdf_document.get_toc(simple=False):
        level, title, page = entry[:3]
        if isinstance(title, str):
            title = re.sub(r"\.pdf(?=(?:_\d+)*$)", "", title, flags=re.IGNORECASE)
        details = [_copy_bookmark_destination(item) for item in entry[3:]]
        new_toc.append([level, title, page] + details)

    pdf_document.set_toc(new_toc, collapse=collapse)
    return pdf_document
