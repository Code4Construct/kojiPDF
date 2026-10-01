import fitz  # PyMuPDF


def make_newentry(entry, position_zoom, bookmark_font):
    level, title, page = entry
    color, bold, italic = bookmark_font
    x, y, zoom = position_zoom

    return [
        level,
        title,
        page,
        {
            "kind": fitz.LINK_GOTO,
            "page": page,
            "to": fitz.Point(x, y),
            "zoom": zoom,
            "color": color,
            "bold": bold,
            "italic": italic,
        },
    ]


def make_newtoc(toc, position_zooms, bookmark_fonts):
    print("しおりデータを作成しています。")
    entries = []

    for entry in toc:
        _level, title, page = entry
        bookmark_font = bookmark_fonts.get((title, page), ((0, 0, 0), False, False))
        position_zoom = position_zooms.get(page)
        if position_zoom is None:
            entries.append(entry)
            continue

        entries.append(make_newentry(entry, position_zoom, bookmark_font))

    return entries


if __name__ == "__main__":
    toc = [
        [1, "sample", 1],
        [2, "sample-child", 2],
    ]
    bookmark_fonts = {
        ("sample", 1): ((0, 0, 0), False, False),
        ("sample-child", 2): ((1, 0, 0), True, False),
    }
    position_zooms = {
        1: (100.0, 100.0, 0),
        2: (0.0, 100.0, 2),
    }
    print(make_newtoc(toc, position_zooms, bookmark_fonts))
