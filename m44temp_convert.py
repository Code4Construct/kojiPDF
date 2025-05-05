import os
import shutil
from pathlib import Path
import m06finish_message as m06
import m43infolder_w_e2pdf as m43

def copy_all_folders_to_temp(folder_path, file_path):
    #file_path の親フォルダをtemp_folder_pathに指定
    pfile_path = Path(file_path)
    print(f"フォルダのパス: {pfile_path.parent}")
    temp_folder_path = str(pfile_path.parent / "temp_folder")
    # temp_folder_path が既に存在する場合は削除
    if os.path.exists(temp_folder_path):
        m06.main(f'暫定フォルダの{temp_folder_path}が既に存在します。\n上書きして続けてよいですか。')
        shutil.rmtree(temp_folder_path)
    os.makedirs(temp_folder_path)

    # folder_path 配下の構造を再帰的に temp_folder_path にコピー
    for root, dirs, files in os.walk(folder_path):
        # 現在の root から folder_path までの相対パスを取得
        relative_path = os.path.relpath(root, folder_path)
        # 対象のコピー先パスを作成
        target_dir = os.path.join(temp_folder_path, relative_path)
        os.makedirs(target_dir, exist_ok=True)

        for file in files:
            src_file = os.path.join(root, file)
            dst_file = os.path.join(target_dir, file)
            shutil.copy2(src_file, dst_file)

    # PDF変換処理
    m43.convert_all_files_to_pdf(temp_folder_path)
    print("PDF変換処理が完了しました。")

    return temp_folder_path

# 使用例
if __name__ == "__main__":
    folder_path = r"F:\01HIROTAKAのデータ\仕事\20250415庶務担当課長会資料 - コピー"  # コピー元フォルダ
    file_path = r"C:\Users\uboni\Desktop\test.txt"  # テンポラリーフォルダ（固定）

    temp_path = copy_all_folders_to_temp(folder_path, file_path)
    print(f"テンポラリーフォルダのパス: {temp_path}")





