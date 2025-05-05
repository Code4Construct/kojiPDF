import os
from fitz import Document  # fitz.open() の代わりに Document クラスを使用
from pandas import DataFrame, ExcelWriter  # pandasの必要な部分のみをインポート

def collect_pdf_paths(folder_path):
    paths = []
    for root, dirs, files in os.walk(folder_path):
        dirs.sort()
        files.sort()
        
        pdf_files = [file for file in files if file.lower().endswith('.pdf')]
        
        if pdf_files:
            for pdf_file in pdf_files:
                paths.append(os.path.join(root, pdf_file))
        elif not dirs:
            paths.append(root)
            
    return paths

def get_pdf_page_count(pdf_path):
    try:
        with Document(pdf_path) as pdf_document:  # fitz.open() の代わりに Document クラスを使用
            return pdf_document.page_count
    except Exception as e:
        print(f"Error opening {pdf_path}: {e}")
        return 0

def main(input_folder):
    """
    指定フォルダ内のPDFファイルを処理し、ファイル情報を含むDataFrameを生成します。

    Args:
        input_folder (str): PDFファイルを含むフォルダのパス。

    Returns:
        tuple:
            - DataFrame: ファイル情報を含むデータフレーム。
                - "Page Count": PDFのページ数（PDF以外は0）。
                - "Full Path": ファイルの絶対パス。
                - "sortpath": ソート用のフルパス。
                - "Level 1", "Level 2", ...: input_folder からのフォルダ階層。
            - int: フォルダの最大階層。
    """
    paths = collect_pdf_paths(input_folder)
    data = []
    for path in paths:
        row = []
        page_count = get_pdf_page_count(path) if path.lower().endswith('.pdf') else 0
        
        row.append(page_count)
        row.append(path)
        row.append(path)
        relative_path = path.replace(input_folder + os.sep, '')
        parts = relative_path.split(os.sep)
        row.extend(parts)

        data.append(row)

    max_levels = max(len(row) - 3 for row in data)
    columns = ["Page Count", "Full Path", "sortpath"] + [f"Level {i+1}" for i in range(max_levels)]
    df = DataFrame(data, columns=columns)
    return df, max_levels

if __name__ == "__main__":
    input_folder = r"F:\バックアップデータ\201603建築企画代理データ"

    df, max_levels = main(input_folder)

    with ExcelWriter('Treedata.xlsx') as writer:
        df.to_excel(writer, index=False)



