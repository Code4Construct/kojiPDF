import os
import shutil
from pathlib import Path
from datetime import datetime
import m06finish_message as m06
import m43infolder_w_e2pdf as m43
import m48mail_to_pdf as mail_exporter

def copy_all_folders_to_temp(
    folder_path,
    file_path,
    ppt_slide_bookmarks=True,
    convert_mail=False,
    eml_encoding="auto",
    issue_report=None,
):
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
        # temp_folder 自身への再帰コピーを防止する
        dirs[:] = [
            directory
            for directory in dirs
            if os.path.abspath(os.path.join(root, directory)) != os.path.abspath(temp_folder_path)
        ]

        # 現在の root から folder_path までの相対パスを取得
        relative_path = os.path.relpath(root, folder_path)
        # 対象のコピー先パスを作成
        target_dir = os.path.join(temp_folder_path, relative_path)
        os.makedirs(target_dir, exist_ok=True)

        for file in files:
            src_file = os.path.join(root, file)
            dst_file = os.path.join(target_dir, file)
            shutil.copy2(src_file, dst_file)

    if convert_mail:
        mail_results = mail_exporter.expand_mail_files_in_folder(
            temp_folder_path,
            temp_folder_path,
            recursive=True,
            eml_encoding=eml_encoding,
        )
        for result in mail_results:
            if result.success:
                print(f"メール展開完了: {result.output}")
                result.source.unlink(missing_ok=True)
            else:
                message = f"メール展開失敗: {result.source} -> {result.error}"
                print(message)
                if issue_report is not None:
                    issue_report.append(
                        {
                            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "category": "Mail conversion error",
                            "message": message,
                        }
                    )

    # PDF変換処理
    m43.convert_all_files_to_pdf(temp_folder_path, ppt_slide_bookmarks, issue_report=issue_report)
    print("PDF変換処理が完了しました。")

    return temp_folder_path

# 使用例
if __name__ == "__main__":
    folder_path = r"F:\01HIROTAKAのデータ\仕事\20250415庶務担当課長会資料 - コピー"  # コピー元フォルダ
    file_path = r"C:\Users\uboni\Desktop\test.txt"  # テンポラリーフォルダ（固定）

    temp_path = copy_all_folders_to_temp(folder_path, file_path)
    print(f"テンポラリーフォルダのパス: {temp_path}")





