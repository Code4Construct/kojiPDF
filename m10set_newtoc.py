import m07make_toc as m07
import m08get_Po_Zs as m08
import m13get_fonts as m13


def set_newtoc(
    pdf_document,
    xratio,
    yratio,
    Ncollapse,
    base_view_width_mm=330,
    base_view_height_mm=210,
    bookmark_view_mode="adjust",
    apply_asper_bookmark_colors=False,
):
    """Apply bookmark destination, zoom, collapse, and font settings."""
    bookmark_fonts = m13.get_fonts(pdf_document, apply_asper_colors=apply_asper_bookmark_colors)
    position_zooms = m08.get_Po_Zs(
        pdf_document,
        xratio,
        yratio,
        base_view_width_mm,
        base_view_height_mm,
    )

    pdf_document.set_toc(
        m07.make_newtoc(pdf_document.get_toc(), position_zooms, bookmark_fonts),
        collapse=Ncollapse,
    )
    return pdf_document


def _pdf_number(value):
    return f"{float(value):.6f}".rstrip("0").rstrip(".")


def apply_bookmark_view_mode(pdf_document, bookmark_view_mode="adjust"):
    if bookmark_view_mode == "adjust":
        return pdf_document

    toc = pdf_document.get_toc(simple=False)
    outline_xrefs = pdf_document.get_outline_xrefs()
    for entry, outline_xref in zip(toc, outline_xrefs):
        if len(entry) < 4:
            continue

        detail = entry[3]
        page_index = detail.get("page")
        if not isinstance(page_index, int) or page_index < 0 or page_index >= pdf_document.page_count:
            page_number = entry[2]
            if not isinstance(page_number, int) or page_number <= 0:
                continue
            page_index = page_number - 1

        page = pdf_document.load_page(page_index)
        page_ref = f"{pdf_document.page_xref(page_index)} 0 R"
        cropbox = page.cropbox

        if bookmark_view_mode == "fit_width":
            destination = f"[{page_ref} /FitH {_pdf_number(cropbox.y1)}]"
        elif bookmark_view_mode == "fit_height":
            destination = f"[{page_ref} /FitV {_pdf_number(cropbox.x0)}]"
        elif bookmark_view_mode == "fit_page":
            destination = f"[{page_ref} /Fit]"
        else:
            continue

        pdf_document.xref_set_key(outline_xref, "A/D", destination)

    return pdf_document
