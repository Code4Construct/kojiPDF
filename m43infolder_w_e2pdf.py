import m40office2pdf as m40
import m41each_file_pathlist as m41
import os
import time

def convert_all_files_to_pdf(folder_path):
    """
    指定されたフォルダ内のすべてのファイル（下位フォルダ含む）をPDFに変換する。

    Parameters:
        folder_path (str): フォルダのパス
    """
    file_list = m41.list_all_files(folder_path)

    for file_path in file_list:
        print(f"変換対象: {file_path}")
        m40.convert_to_pdf(file_path)
        time.sleep(1)

if __name__ == "__main__":
    convert_all_files_to_pdf(r"F:\01HIROTAKAのデータ\仕事\20250415庶務担当課長会資料 - コピー")