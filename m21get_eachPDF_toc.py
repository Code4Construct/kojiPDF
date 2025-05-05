import os
from fitz import Document  # fitz = PyMuPDF
import pandas as pd
from pandas import read_excel

def get_each_pdf_toc(df):
    """
    各PDFファイルのTOC（しおり）を取得し、pageとpdf_titleをキーにして辞書で返す。
    'Level 1', 'Level 2', ... などの列を自動検出します。

    Parameters:
        df (pd.DataFrame): PDFファイル情報を含むDataFrame

    Returns:
        dict: {(page, pdf_title): toc} の形式の辞書
              tocが空のものは含まれない
    """
    results = {}

    # MultiIndex対応
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [' '.join(col).strip() for col in df.columns.values]
    
    if 'Full Path' not in df.columns:
        raise ValueError("DataFrameに 'Full Path' 列が見つかりません。")

    # Level列を自動検出（'Level 1', 'Level 2', ...）
    level_cols = [col for col in df.columns if col.strip().startswith("Level ")]
    level_cols.sort(key=lambda x: int(x.split()[-1]))  # 順番を保証
    N = len(level_cols)

    for index, row in df.iterrows():
        page = row.get('Page All', None)
        if page is None:
            continue
        page += 1  # Page番号調整

        path = row.get('Full Path', None)
        levels = [row.get(f'Level {i + 1}', "") for i in range(N)]
        pdf_title = next(
            (level for level in reversed(levels) if isinstance(level, str) and level.lower().endswith('.pdf')),
            None
        )

        if not path or not os.path.exists(path) or not pdf_title:
            continue

        try:
            with Document(path) as pdf_document:
                toc = pdf_document.get_toc()
                if toc:  # tocが空でなければ追加
                    results[(page, pdf_title)] = toc

        except Exception as e:
            print(f"[エラー] PDFを処理中に問題が発生しました: {path} - {e}")
    
    return results

# テスト用
if __name__ == '__main__':
    df = read_excel(r"F:\learning_python\pdftool\bookmark_from_folderv6_v110\Treedata.xlsx")
    toc_dict = get_each_pdf_toc(df)

    for (page, title), toc in toc_dict.items():
        print(f"{page} - {title}")
        for item in toc:
            print("  ", item)



