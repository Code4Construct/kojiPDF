import fitz


def add_numbers_to_bookmarks(output_pdf, add_bookmark_page_number=False, add_included_page_count=False):
    """Append selected numeric suffixes to bookmark titles."""
    if not add_bookmark_page_number and not add_included_page_count:
        return output_pdf

    toc = output_pdf.get_toc()
    new_toc = []

    for i, entry in enumerate(toc):
        level, title, page = entry[:3]
        suffix_parts = []

        if add_bookmark_page_number:
            suffix_parts.append(str(page))

        if add_included_page_count:
            next_page = output_pdf.page_count + 1
            for j in range(i + 1, len(toc)):
                if toc[j][0] <= level:
                    next_page = toc[j][2]
                    break
            suffix_parts.append(str(next_page - page))

        new_title = f"{title}_{'_'.join(suffix_parts)}" if suffix_parts else title
        new_toc.append([level, new_title, page] + entry[3:])

    output_pdf.set_toc(new_toc)
    return output_pdf


def add_page_number_to_bookmarks(output_pdf):
    return add_numbers_to_bookmarks(output_pdf, add_included_page_count=True)


if __name__ == "__main__":
    input_path = r"C:\Users\uboni\Desktop\testtemp.PDF"
    output_path = r"C:\Users\uboni\Desktop\testnum.PDF"

    output_pdf = fitz.open(input_path)
    output_pdf = add_numbers_to_bookmarks(
        output_pdf,
        add_bookmark_page_number=True,
        add_included_page_count=True,
    )
    output_pdf.save(output_path)
    output_pdf.close()
