import os

def list_all_files(folder_path):
    """
    指定されたフォルダ内のすべてのファイル（下位フォルダ含む）のパスをリストで返す。

    Parameters:
        folder_path (str): フォルダのパス

    Returns:
        List[str]: ファイルパスのリスト
    """
    all_files = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            full_path = os.path.join(root, file)
            all_files.append(full_path)
    return all_files

# 使用例（スクリプトとして実行したとき）
if __name__ == "__main__":
    file_list = list_all_files(r"f:\01HIROTAKAのデータ\仕事\20160820空家計画")
    for f in file_list:
        print(f)
