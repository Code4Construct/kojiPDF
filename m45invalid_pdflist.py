import os
from fitz import Document
from fitz.fitz import FileDataError, EmptyFileError

def find_invalid_pdfs_with_errors(folder_path):
    """
    指定フォルダ内のPDFファイルのうち、fitzで開けないものや
    サイズ0のファイルなど、問題のあるPDFとそのエラーメッセージのリストを返す。

    Args:
        folder_path (str): 対象フォルダのパス

    Returns:
        List[Tuple[str, str]]: (ファイルパス, エラーメッセージ) のリスト
    """
    invalid_files = []

    for root, _, files in os.walk(folder_path):
        for file in files:
            if not file.lower().endswith('.pdf'):
                continue

            full_path = os.path.join(root, file)

            if not os.path.isfile(full_path):
                invalid_files.append((full_path, "Not a file"))
            elif os.path.getsize(full_path) == 0:
                invalid_files.append((full_path, "File size is 0"))
            else:
                try:
                    with Document(full_path) as pdf:
                        _ = pdf.page_count  # ページ数参照で読み込み確認
                except EmptyFileError as e:
                    invalid_files.append((full_path, f"EmptyFileError: {str(e)}"))
                except FileDataError as e:
                    invalid_files.append((full_path, f"FileDataError: {str(e)}"))
                except Exception as e:
                    invalid_files.append((full_path, f"Other error: {str(e)}"))

    return invalid_files


if __name__ == "__main__":
    folder_path = r"F:\01HIROTAKAのデータ\仕事\20161120協議会資料\スタッフ資料"

    if not os.path.isdir(folder_path):
        print("❌ 入力されたフォルダパスは存在しません。")
    else:
        invalids = find_invalid_pdfs_with_errors(folder_path)
        if invalids:
            print("\n❌ 問題のあるPDFファイル一覧:")
            for path, msg in invalids:
                print(f" - {path} → {msg}")
        else:
            print("✅ すべてのPDFファイルは正常に読み込めます。")



