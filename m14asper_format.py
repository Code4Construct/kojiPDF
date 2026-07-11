import re


def modify_pdf_names_in_all_columns(df):
    """
    電脳ASPerの出力名を、しおり表示用・ソート用に整えます。

    Full Path は実ファイル参照に使うため変更しません。
    """

    def modify_name(value):
        if isinstance(value, str):
            if value.endswith(".pdf"):
                value = value.replace("【本文】", "")
                value = value.replace("【鑑】", "ｶ鑑_")
                value = re.sub(r"【添付(\d+)】", r"ﾃ\1_", value)
                value = re.sub(r"^00(\d{2})-", r"", value)
            else:
                value = re.sub(r"^(\d{2})-", r"", value)
        return value

    rows = []
    for row in df:
        new_row = row.copy()
        for column, value in row.items():
            if column != "Full Path":
                new_row[column] = modify_name(value)
        rows.append(new_row)

    return rows


def last_bookmarks_rename(output_pdf):
    """
    電脳ASPer向けに、PDFのしおり名を最終調整します。
    """
    toc = output_pdf.get_toc()
    new_toc = []

    for entry in toc:
        level, title, page = entry[:3]

        if title.startswith("ｶ鑑_"):
            title = "打_" + title[3:]
        elif len(title) > 4 and title[0] == "ﾃ" and title[1:3].isdigit() and title[3] == "_":
            title = title[4:]

        new_toc.append([level, title, page] + entry[3:])

    output_pdf.set_toc(new_toc)
    return output_pdf
