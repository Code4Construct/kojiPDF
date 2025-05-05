import os
from fitz import Document
from pandas import read_excel

def merge_pdfs_from_df(df):
    """
    データフレームの指定列にあるPDFファイルを結合して1つのPDFファイルを作成します。
    """
    output_pdf = Document()
    paths = df['Full Path']
    print(f"　{len(paths)} のPDFファイルを結合しています。")

    for path in paths:
        if (
            isinstance(path, str) and
            os.path.isfile(path) and
            path.lower().endswith('.pdf') and
            os.path.getsize(path) > 0
        ):
            try:
                with Document(path) as pdf:
                    for page_num in range(pdf.page_count):
                        output_pdf.insert_pdf(pdf, from_page=page_num, to_page=page_num)
            except Exception as e:
                print(f"⚠️ エラー: {path} の読み込みに失敗しました → {e}")
        else:
            print(f"⚠️ スキップ: {path}（存在しない・PDFでない・空ファイル）")

    return output_pdf

if __name__ == '__main__':
    excel_path = "Treedata.xlsx"
    df = read_excel(excel_path, sheet_name=0)
    output_pdf_path = "merged_output.pdf"

    output_pdf = merge_pdfs_from_df(df)
    output_pdf.save(output_pdf_path)
    output_pdf.close()
    
    print(f"Merged PDF saved as {output_pdf_path}")

