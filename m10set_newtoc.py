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
