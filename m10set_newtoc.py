import fitz  # PyMuPDF evalで文字列なので、認識しないが必要
import m07make_toc as m07
import m08get_Po_Zs as m08
import m13get_fonts as m13
#globals()["fitz"] = fitz  # eval() で fitz を使えるようにする
def set_newtoc(pdf_document,xratio,yratio):
    """
    PDF ドキュメントの目次 (TOC) にリンク情報を設定し、画面にフィットするように調整された PDF を返します。

    この関数は以下の処理を行います:
    1. `get_Po_Zs` を用いて、各ページの表示位置 (x, y) およびズーム倍率 (z) を取得します。
    2. `make_newtoc` を使用し、元の TOC にリンク情報を追加した新しい TOC を生成します。
    3. `set_toc` により PDF ドキュメントに新しい TOC を適用します。

    各リンクは、指定された倍率 `xratio`, `yratio` に基づいて、画面にフィットするように設定されます。

    Args:
        pdf_document (fitz.Document): 編集対象の PDF ドキュメント。
        xratio (float): ページ幅に対するズーム倍率。
        yratio (float): ページ高さに対するズーム倍率。

    Returns:
        fitz.Document: TOC にリンク情報が設定された PDF ドキュメント。

    Note:
        `make_newtoc` の戻り値は文字列であり、`eval()` を用いて辞書に変換されます。
    """
    Bfonts = m13.get_fonts(pdf_document)
    Po_Zs = m08.get_Po_Zs(pdf_document,xratio,yratio)
    #print(Po_Zs)
    pdf_document.set_toc(eval(m07.make_newtoc(pdf_document.get_toc(),Po_Zs,Bfonts)))
    return pdf_document